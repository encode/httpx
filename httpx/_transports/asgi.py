import typing
from contextlib import AsyncExitStack, asynccontextmanager

import sniffio

from .._models import Request, Response
from .._types import AsyncByteStream
from .base import AsyncBaseTransport

try:
    import anyio
except ImportError:  # pragma: no cover
    anyio = None  # type: ignore


if typing.TYPE_CHECKING:  # pragma: no cover
    import asyncio

    import trio

    Event = typing.Union[asyncio.Event, trio.Event]


_Message = typing.Dict[str, typing.Any]
_Receive = typing.Callable[[], typing.Awaitable[_Message]]
_Send = typing.Callable[
    [typing.Dict[str, typing.Any]], typing.Coroutine[None, None, None]
]
_ASGIApp = typing.Callable[
    [typing.Dict[str, typing.Any], _Receive, _Send], typing.Coroutine[None, None, None]
]


def create_event() -> "Event":
    if sniffio.current_async_library() == "trio":
        import trio

        return trio.Event()
    else:
        import asyncio

        return asyncio.Event()


class ASGIResponseByteStream(AsyncByteStream):
    def __init__(
        self, stream: typing.AsyncGenerator[bytes, None], app_context: AsyncExitStack
    ) -> None:
        self._stream = stream
        self._app_context = app_context

    def __aiter__(self) -> typing.AsyncIterator[bytes]:
        return self._stream.__aiter__()

    async def aclose(self) -> None:
        await self._stream.aclose()
        await self._app_context.aclose()


class ASGITransport(AsyncBaseTransport):
    """
    A custom AsyncTransport that handles sending requests directly to an ASGI app.
    The simplest way to use this functionality is to use the `app` argument.

    ```
    client = httpx.AsyncClient(app=app)
    ```

    Alternatively, you can setup the transport instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the ASGITransport class:

    ```
    transport = httpx.ASGITransport(
        app=app,
        root_path="/submount",
        client=("1.2.3.4", 123)
    )
    client = httpx.AsyncClient(transport=transport)
    ```

    Arguments:

    * `app` - The ASGI application.
    * `raise_app_exceptions` - Boolean indicating if exceptions in the application
       should be raised. Default to `True`. Can be set to `False` for use cases
       such as testing the content of a client 500 response.
    * `root_path` - The root path on which the ASGI application should be mounted.
    * `client` - A two-tuple indicating the client IP and port of incoming requests.
    ```
    """

    def __init__(
        self,
        app: _ASGIApp,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: typing.Tuple[str, int] = ("127.0.0.1", 123),
    ) -> None:
        if anyio is None:
            raise RuntimeError("ASGITransport requires anyio (Hint: pip install anyio)")

        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        exit_stack = AsyncExitStack()

        (
            status_code,
            response_headers,
            response_body,
        ) = await exit_stack.enter_async_context(
            run_asgi(
                self.app,
                raise_app_exceptions=self.raise_app_exceptions,
                root_path=self.root_path,
                client=self.client,
                request=request,
            )
        )

        return Response(
            status_code,
            headers=response_headers,
            stream=ASGIResponseByteStream(response_body, exit_stack),
        )


@asynccontextmanager
async def run_asgi(
    app: _ASGIApp,
    raise_app_exceptions: bool,
    client: typing.Tuple[str, int],
    root_path: str,
    request: Request,
) -> typing.AsyncIterator[
    typing.Tuple[
        int,
        typing.Sequence[typing.Tuple[bytes, bytes]],
        typing.AsyncGenerator[bytes, None],
    ]
]:
    # ASGI scope.
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": request.method,
        "headers": [(k.lower(), v) for (k, v) in request.headers.raw],
        "scheme": request.url.scheme,
        "path": request.url.path,
        "raw_path": request.url.raw_path,
        "query_string": request.url.query,
        "server": (request.url.host, request.url.port),
        "client": client,
        "root_path": root_path,
    }

    # Request.
    assert isinstance(request.stream, AsyncByteStream)
    request_body_chunks = request.stream.__aiter__()
    request_complete = False

    # Response.
    status_code = None
    response_headers = None
    response_started = anyio.Event()
    response_complete = anyio.Event()

    send_stream, receive_stream = anyio.create_memory_object_stream()
    disconnected = anyio.Event()

    async def watch_disconnect(cancel_scope: anyio.CancelScope) -> None:
        await disconnected.wait()
        cancel_scope.cancel()

    async def run_app(cancel_scope: anyio.CancelScope) -> None:
        try:
            await app(scope, receive, send)
        except Exception:  # noqa: PIE-786
            cancel_scope.cancel()

            if raise_app_exceptions or not response_complete.is_set():
                raise

    # ASGI callables.

    async def receive() -> typing.Dict[str, typing.Any]:
        nonlocal request_complete

        if request_complete:
            await response_complete.wait()
            return {"type": "http.disconnect"}

        try:
            body = await request_body_chunks.__anext__()
        except StopAsyncIteration:
            request_complete = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": body, "more_body": True}

    async def send(message: _Message) -> None:
        nonlocal status_code, response_headers

        if disconnected.is_set():
            await anyio.sleep(
                0
            )  # temp fix - yield control for disconnect watcher when loop is tight
            return

        if message["type"] == "http.response.start":
            assert not response_started.is_set()

            status_code = message["status"]
            response_headers = message.get("headers", [])
            response_started.set()

        elif message["type"] == "http.response.body":
            assert response_started.is_set()
            assert not response_complete.is_set()
            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            if body and request.method != "HEAD":
                await send_stream.send(body)

            if not more_body:
                response_complete.set()
                await send_stream.aclose()

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(watch_disconnect, tg.cancel_scope)
            tg.start_soon(run_app, tg.cancel_scope)

            await response_started.wait()
            assert status_code is not None
            assert response_headers is not None

            async def stream() -> typing.AsyncGenerator[bytes, None]:
                async for chunk in receive_stream:
                    yield chunk

            yield (status_code, response_headers, stream())
            disconnected.set()
    except ExceptionGroup as exc_group:
        raise exc_group.exceptions[0]  # only run_app should raise exceptions
    finally:
        disconnected.set()
        await send_stream.aclose()
        await receive_stream.aclose()
