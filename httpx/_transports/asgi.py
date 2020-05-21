import typing
from typing import Callable, Dict, List, Optional, Tuple

import httpcore
import sniffio

from .._content_streams import ByteStream
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
        request_complete = False
        response_started = False
        response_complete = create_event()

        headers = [] if headers is None else headers
        stream = ByteStream(b"") if stream is None else stream

        request_body_chunks = stream.__aiter__()

        async def receive() -> dict:
            nonlocal request_complete, response_complete

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
            nonlocal status_code, response_headers, body_parts
            nonlocal response_started, response_complete

            if message["type"] == "http.response.start":
                assert not response_started

                status_code = message["status"]
                response_headers = message.get("headers", [])
                response_started = True

            elif message["type"] == "http.response.body":
                assert not response_complete.is_set()
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and method != b"HEAD":
                    body_parts.append(body)

                if not more_body:
                    response_complete.set()

        try:
            await self.app(scope, receive, send)
        except Exception:
            if self.raise_app_exceptions or not response_complete:
                raise

        assert response_complete.is_set()
        assert status_code is not None
        assert response_headers is not None

        stream = ByteStream(b"".join(body_parts))

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
