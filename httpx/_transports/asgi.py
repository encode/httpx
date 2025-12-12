from __future__ import annotations

import contextlib
import typing

from .._models import Request, Response
from .._types import AsyncByteStream
from .base import AsyncBaseTransport

if typing.TYPE_CHECKING:  # pragma: no cover
    import asyncio

    import anyio.abc
    import anyio.streams.memory
    import trio

    Event = typing.Union[asyncio.Event, trio.Event]
    MessageReceiveStream = typing.Union[
        anyio.streams.memory.MemoryObjectReceiveStream["_Message"],
        trio.MemoryReceiveChannel["_Message"],
    ]
    MessageSendStream = typing.Union[
        anyio.streams.memory.MemoryObjectSendStream["_Message"],
        trio.MemorySendChannel["_Message"],
    ]
    TaskGroup = typing.Union[anyio.abc.TaskGroup, trio.Nursery]


_Message = typing.MutableMapping[str, typing.Any]
_Receive = typing.Callable[[], typing.Awaitable[_Message]]
_Send = typing.Callable[[_Message], typing.Awaitable[None]]
_ASGIApp = typing.Callable[
    [typing.MutableMapping[str, typing.Any], _Receive, _Send], typing.Awaitable[None]
]

__all__ = ["ASGITransport"]


def is_running_trio() -> bool:
    try:
        # sniffio is a dependency of trio.

        # See https://github.com/python-trio/trio/issues/2802
        import sniffio

        if sniffio.current_async_library() == "trio":
            return True
    except ImportError:  # pragma: nocover
        pass

    return False


def create_event() -> Event:
    if is_running_trio():
        import trio

        return trio.Event()

    import asyncio

    return asyncio.Event()


def create_memory_object_stream(
    max_buffer_size: float,
) -> tuple[MessageSendStream, MessageReceiveStream]:
    if is_running_trio():
        import trio

        return trio.open_memory_channel(max_buffer_size)

    import anyio

    return anyio.create_memory_object_stream(max_buffer_size)


def create_task_group() -> typing.AsyncContextManager[TaskGroup]:
    if is_running_trio():
        import trio

        return trio.open_nursery()

    import anyio

    return anyio.create_task_group()


def get_end_of_stream_error_type() -> type[anyio.EndOfStream | trio.EndOfChannel]:
    if is_running_trio():
        import trio

        return trio.EndOfChannel

    import anyio

    return anyio.EndOfStream


class ASGIResponseStream(AsyncByteStream):
    def __init__(
        self,
        ignore_body: bool,
        asgi_generator: typing.AsyncGenerator[_Message, None],
    ) -> None:
        self._ignore_body = ignore_body
        self._asgi_generator = asgi_generator

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        more_body = True
        try:
            async for message in self._asgi_generator:
                assert message["type"] != "http.response.start"
                if message["type"] == "http.response.body":
                    assert more_body
                    chunk = message.get("body", b"")
                    more_body = message.get("more_body", False)
                    if chunk and not self._ignore_body:
                        yield chunk
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        await self._asgi_generator.aclose()


class ASGITransport(AsyncBaseTransport):
    """
    A custom AsyncTransport that handles sending requests directly to an ASGI app.

    ```python
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
    * `streaming` - Set to `True` to enable streaming of response content. Default to
      `False`, as activating this feature means that the ASGI `app` will run in a
      sub-task, which has observable side effects for context variables.
    ```
    """

    def __init__(
        self,
        app: _ASGIApp,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: tuple[str, int] = ("127.0.0.1", 123),
        *,
        streaming: bool = False,
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client
        self.streaming = streaming

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        asgi_generator = self._stream_asgi_messages(request)

        async for message in asgi_generator:
            if message["type"] == "http.response.start":
                return Response(
                    status_code=message["status"],
                    headers=message.get("headers", []),
                    stream=ASGIResponseStream(
                        ignore_body=request.method == "HEAD",
                        asgi_generator=asgi_generator,
                    ),
                )
        else:
            return Response(status_code=500, headers=[])

    async def _stream_asgi_messages(
        self, request: Request
    ) -> typing.AsyncGenerator[typing.MutableMapping[str, typing.Any]]:
        assert isinstance(request.stream, AsyncByteStream)

        # ASGI scope.
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": [(k.lower(), v) for (k, v) in request.headers.raw],
            "scheme": request.url.scheme,
            "path": request.url.path,
            "raw_path": request.url.raw_path.split(b"?")[0],
            "query_string": request.url.query,
            "server": (request.url.host, request.url.port),
            "client": self.client,
            "root_path": self.root_path,
        }

        # Request.
        request_body_chunks = request.stream.__aiter__()
        request_complete = False

        # Response.
        response_complete = create_event()

        # ASGI response messages stream
        stream_size = 0 if self.streaming else float("inf")
        response_message_send_stream, response_message_recv_stream = (
            create_memory_object_stream(stream_size)
        )

        # ASGI app exception
        app_exception: Exception | None = None

        # ASGI callables.

        async def receive() -> _Message:
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
            await response_message_send_stream.send(message)
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                response_complete.set()

        async def run_app() -> None:
            nonlocal app_exception
            try:
                await self.app(scope, receive, send)
            except Exception as ex:
                app_exception = ex
            finally:
                await response_message_send_stream.aclose()

        async with contextlib.AsyncExitStack() as exit_stack:
            exit_stack.callback(response_complete.set)
            if self.streaming:
                task_group = await exit_stack.enter_async_context(create_task_group())
                task_group.start_soon(run_app)
            else:
                await run_app()

            async with response_message_recv_stream:
                try:
                    while True:
                        message = await response_message_recv_stream.receive()
                        yield message
                except get_end_of_stream_error_type():
                    pass

        if app_exception is not None and self.raise_app_exceptions:
            raise app_exception
