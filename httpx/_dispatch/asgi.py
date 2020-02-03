from typing import Callable, List, Tuple

from .._config import TimeoutTypes
from .._content_streams import ByteStream, ContentStream
from .._models import URL
from .base import AsyncDispatcher


class ASGIDispatch(AsyncDispatcher):
    """
    A custom AsyncDispatcher that handles sending requests directly to an ASGI app.
    The simplest way to use this functionality is to use the `app` argument.

    ```
    client = httpx.AsyncClient(app=app)
    ```

    Alternatively, you can setup the dispatch instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the ASGIDispatch class:

    ```
    dispatch = httpx.ASGIDispatch(
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

    async def send(
        self,
        method: bytes,
        url: URL,
        headers: List[Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: TimeoutTypes = None,
    ) -> Tuple[int, str, List[Tuple[bytes, bytes]], ContentStream]:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.decode(),
            "headers": headers,
            "scheme": url.scheme,
            "path": url.path,
            "query_string": url.query.encode("ascii"),
            "server": url.host,
            "client": self.client,
            "root_path": self.root_path,
        }
        status_code = None
        response_headers = None
        body_parts = []
        response_started = False
        response_complete = False

        request_body_chunks = stream.__aiter__()

        async def receive() -> dict:
            try:
                body = await request_body_chunks.__anext__()
            except StopAsyncIteration:
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
                assert not response_complete
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and method != b"HEAD":
                    body_parts.append(body)

                if not more_body:
                    response_complete = True

        try:
            await self.app(scope, receive, send)
        except Exception:
            if self.raise_app_exceptions or not response_complete:
                raise

        assert response_complete
        assert status_code is not None
        assert response_headers is not None

        stream = ByteStream(b"".join(body_parts))

        return (status_code, "HTTP/1.1", response_headers, stream)
