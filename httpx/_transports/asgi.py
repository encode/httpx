import typing
from typing import Callable, Dict, List, Optional, Tuple, cast

import httpcore
import sniffio

from .._content_streams import AsyncIteratorStream, ByteStream, ContentStream
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
        body_parts = []
        body_parts_event = create_event()
        request_complete = False
        response_started = create_event()
        response_complete = create_event()

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
                    body_parts.append(body)
                    body_parts_event.set()

                if not more_body:
                    response_complete.set()

        def handle_exception(ex: Exception) -> None:
            if self.raise_app_exceptions or not response_complete:
                raise ex from None

        response_stream: ContentStream
        if sniffio.current_async_library() == "asyncio":
            import asyncio

            # Tasks need to be created to run the coroutines in the background
            loop = asyncio.get_event_loop()
            app_task = loop.create_task(self.app(scope, receive, send))
            response_task = loop.create_task(response_started.wait())
            done, pending = await asyncio.wait(
                [app_task, response_task], return_when=asyncio.FIRST_COMPLETED
            )

            if response_task in done:

                async def response_generator() -> typing.AsyncIterator[bytes]:
                    while True:
                        if body_parts:
                            # Body parts immediately available, yield and continue
                            yield body_parts.pop(0)
                            continue
                        # Wait for either more body parts or request to finish
                        body_parts_task = loop.create_task(body_parts_event.wait())
                        done, pending = await asyncio.wait(
                            [app_task, body_parts_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if app_task in done and body_parts_task in pending:
                            # Application finished and no more body parts available
                            body_parts_task.cancel()
                            break
                        cast(asyncio.Event, body_parts_event).clear()
                    try:
                        # Make sure the application task is joined before finishing
                        await app_task
                    except Exception as ex:
                        handle_exception(ex)

                assert response_started.is_set()
                response_stream = AsyncIteratorStream(response_generator())
            else:
                # Application finished in the middle of making the request
                response_task.cancel()
                try:
                    await app_task
                except Exception as ex:
                    handle_exception(ex)

                assert response_complete.is_set()
                response_stream = ByteStream(b"".join(body_parts))
        else:
            try:
                await self.app(scope, receive, send)
            except Exception as ex:
                handle_exception(ex)

            assert response_complete.is_set()
            response_stream = ByteStream(b"".join(body_parts))

        assert status_code is not None
        assert response_headers is not None

        return (b"HTTP/1.1", status_code, b"", response_headers, response_stream)


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
