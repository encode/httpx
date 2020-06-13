import contextlib
from typing import (
    TYPE_CHECKING,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import httpcore
import sniffio

from .._content_streams import AsyncIteratorStream, ByteStream
from .._utils import warn_deprecated

if TYPE_CHECKING:
    import asyncio
    import trio

    Event = Union[asyncio.Event, trio.Event]


def create_event() -> "Event":
    if sniffio.current_async_library() == "trio":
        import trio

        return trio.Event()
    else:
        import asyncio

        return asyncio.Event()


async def create_background_task(
    async_fn: Callable[[], Awaitable[None]]
) -> Callable[[], Awaitable[None]]:
    if sniffio.current_async_library() == "trio":
        import trio

        nursery_manager = trio.open_nursery()
        nursery = await nursery_manager.__aenter__()
        nursery.start_soon(async_fn)

        async def aclose() -> None:
            await nursery_manager.__aexit__(None, None, None)

        return aclose

    else:
        import asyncio

        loop = asyncio.get_event_loop()
        task = loop.create_task(async_fn())

        async def aclose() -> None:
            task.cancel()
            # Task must be awaited in all cases to avoid debug warnings.
            with contextlib.suppress(asyncio.CancelledError):
                await task

        return aclose


def create_channel(
    capacity: int,
) -> Tuple[
    Callable[[bytes], Awaitable[None]],
    Callable[[], Awaitable[None]],
    Callable[[], AsyncIterator[bytes]],
]:
    """
    Create an in-memory channel to pass data chunks between tasks.

    * `produce()`: send data through the channel, blocking if necessary.
    * `consume()`: iterate over data in the channel.
    * `aclose_produce()`: mark that no more data will be produced, causing
    `consume()` to flush remaining data chunks then stop.
    """
    if sniffio.current_async_library() == "trio":
        import trio

        send_channel, receive_channel = trio.open_memory_channel[bytes](capacity)

        async def consume() -> AsyncIterator[bytes]:
            async for chunk in receive_channel:
                yield chunk

        return send_channel.send, send_channel.aclose, consume

    else:
        import asyncio

        queue: asyncio.Queue[bytes] = asyncio.Queue(capacity)
        produce_closed = False

        async def produce(chunk: bytes) -> None:
            assert not produce_closed
            await queue.put(chunk)

        async def aclose_produce() -> None:
            nonlocal produce_closed
            await queue.put(b"")  # Make sure (*) doesn't block forever.
            produce_closed = True

        async def consume() -> AsyncIterator[bytes]:
            while True:
                if produce_closed and queue.empty():
                    break
                yield await queue.get()  # (*)

        return produce, aclose_produce, consume


class ASGITransport(httpcore.AsyncHTTPTransport):
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
        headers = [] if headers is None else headers
        stream = ByteStream(b"") if stream is None else stream

        # Prepare ASGI scope.
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

        # Request.
        request_body_chunks = stream.__aiter__()
        request_complete = False

        # Response.
        response_headers: Optional[List[Tuple[bytes, bytes]]] = None
        status_code: Optional[int] = None
        response_started_or_app_crashed = create_event()
        produce_body, aclose_body, consume_body = create_channel(1)
        response_complete = create_event()

        # ASGI receive/send callables.

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
                assert not response_started_or_app_crashed.is_set()
                status_code = message["status"]
                response_headers = message.get("headers", [])
                response_started_or_app_crashed.set()

            elif message["type"] == "http.response.body":
                assert not response_complete.is_set()
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and method != b"HEAD":
                    await produce_body(body)

                if not more_body:
                    await aclose_body()
                    response_complete.set()

        # Application wrapper.

        app_exception: Optional[Exception] = None

        async def run_app() -> None:
            nonlocal app_exception
            try:
                await self.app(scope, receive, send)
            except Exception as exc:
                app_exception = exc
                response_started_or_app_crashed.set()
                await aclose_body()  # Stop response body consumer once flushed (*).

        # Response body iterator.

        async def aiter_response_body() -> AsyncIterator[bytes]:
            async for chunk in consume_body():  # (*)
                yield chunk

            if app_exception is not None and self.raise_app_exceptions:
                raise app_exception

        # Now we wire things up...

        aclose = await create_background_task(run_app)

        await response_started_or_app_crashed.wait()

        if app_exception is not None:
            await aclose()
            if self.raise_app_exceptions:
                raise app_exception

        assert status_code is not None
        assert response_headers is not None

        stream = AsyncIteratorStream(aiter_response_body(), close_func=aclose)

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
