import typing
from typing import Callable, Dict, List, Optional, Tuple

import httpcore
import sniffio

from .._content_streams import AsyncIteratorStream, ByteStream
from .._utils import warn_deprecated

if typing.TYPE_CHECKING:  # pragma: no cover
    import asyncio
    import trio

    Event = typing.Union[asyncio.Event, trio.Event]


def create_event() -> "Event":
    if sniffio.current_async_library() == "trio":
        import trio

        return trio.Event()
    else:
        import asyncio

        return asyncio.Event()


async def create_background_task(async_fn: typing.Callable) -> typing.Callable:
    if sniffio.current_async_library() == "trio":
        import trio

        nursery_manager = trio.open_nursery()
        nursery = await nursery_manager.__aenter__()
        nursery.start_soon(async_fn)

        async def aclose(exc: Exception = None) -> None:
            if exc is not None:
                await nursery_manager.__aexit__(type(exc), exc, exc.__traceback__)
            else:
                await nursery_manager.__aexit__(None, None, None)

        return aclose

    else:
        import asyncio

        task = asyncio.create_task(async_fn())

        async def aclose(exc: Exception = None) -> None:
            if not task.done():
                task.cancel()

        return aclose


def create_channel(
    capacity: int,
) -> typing.Tuple[
    typing.Callable[[], typing.Awaitable[bytes]],
    typing.Callable[[bytes], typing.Awaitable[None]],
]:
    if sniffio.current_async_library() == "trio":
        import trio

        send_channel, receive_channel = trio.open_memory_channel[bytes](capacity)
        return receive_channel.receive, send_channel.send

    else:
        import asyncio

        queue: asyncio.Queue[bytes] = asyncio.Queue(capacity)
        return queue.get, queue.put


async def run_until_first_complete(*async_fns: typing.Callable) -> None:
    if sniffio.current_async_library() == "trio":
        import trio

        async with trio.open_nursery() as nursery:

            async def run(async_fn: typing.Callable) -> None:
                await async_fn()
                nursery.cancel_scope.cancel()

            for async_fn in async_fns:
                nursery.start_soon(run, async_fn)

    else:
        import asyncio

        coros = [async_fn() for async_fn in async_fns]
        done, pending = await asyncio.wait(coros, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()


class ASGITransport(httpcore.AsyncHTTPTransport):
    """
    A custom AsyncTransport that handles sending requests directly to an ASGI app.
    The simplest way to use this functionality is to use the `app` argument.

    ```
    client = httpx.AsyncClient(app=app)
    ```

    Alternatively, you can setup the dispatch instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the ASGITransport class:

    ```
    dispatch = httpx.ASGITransport(
        app=app,
        root_path="/submount",
        client=("1.2.3.4", 123)
    )
    client = httpx.AsyncClient(dispatch=dispatch)
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
        app: Callable,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: Tuple[str, int] = ("127.0.0.1", 123),
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client

    async def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: Dict[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream]:
        scheme, host, port, full_path = url
        path, _, query = full_path.partition(b"?")
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.decode(),
            "headers": headers,
            "scheme": scheme.decode("ascii"),
            "path": path.decode("ascii"),
            "query_string": query,
            "server": (host.decode("ascii"), port),
            "client": self.client,
            "root_path": self.root_path,
        }
        status_code = None
        response_headers = None
        consume_response_body_chunk, produce_response_body_chunk = create_channel(1)
        request_complete = False
        response_started = create_event()
        response_complete = create_event()
        app_crashed = create_event()
        app_exception: typing.Optional[Exception] = None

        headers = [] if headers is None else headers
        stream = ByteStream(b"") if stream is None else stream

        request_body_chunks = stream.__aiter__()

        async def receive() -> dict:
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

        async def send(message: dict) -> None:
            nonlocal status_code, response_headers

            if message["type"] == "http.response.start":
                assert not response_started.is_set()

                status_code = message["status"]
                response_headers = message.get("headers", [])
                response_started.set()

            elif message["type"] == "http.response.body":
                assert not response_complete.is_set()
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and method != b"HEAD":
                    await produce_response_body_chunk(body)

                if not more_body:
                    response_complete.set()

        async def run_app() -> None:
            nonlocal app_exception
            try:
                await self.app(scope, receive, send)
            except Exception as exc:
                app_exception = exc
                app_crashed.set()

        aclose_app = await create_background_task(run_app)

        await run_until_first_complete(app_crashed.wait, response_started.wait)

        if app_crashed.is_set():
            assert app_exception is not None
            await aclose_app(app_exception)
            if self.raise_app_exceptions or not response_started.is_set():
                raise app_exception

        assert response_started.is_set()
        assert status_code is not None
        assert response_headers is not None

        async def aiter_response_body_chunks() -> typing.AsyncIterator[bytes]:
            chunk = b""

            async def consume_chunk() -> None:
                nonlocal chunk
                chunk = await consume_response_body_chunk()

            while True:
                await run_until_first_complete(
                    app_crashed.wait, consume_chunk, response_complete.wait
                )

                if app_crashed.is_set():
                    assert app_exception is not None
                    if self.raise_app_exceptions:
                        raise app_exception
                    else:
                        break

                yield chunk

                if response_complete.is_set():
                    break

        async def aclose() -> None:
            await aclose_app(app_exception)

        stream = AsyncIteratorStream(aiter_response_body_chunks(), close_func=aclose)

        return (b"HTTP/1.1", status_code, b"", response_headers, stream)


class ASGIDispatch(ASGITransport):
    def __init__(
        self,
        app: Callable,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: Tuple[str, int] = ("127.0.0.1", 123),
    ) -> None:
        warn_deprecated("ASGIDispatch is deprecated, please use ASGITransport")
        super().__init__(
            app=app,
            raise_app_exceptions=raise_app_exceptions,
            root_path=root_path,
            client=client,
        )
