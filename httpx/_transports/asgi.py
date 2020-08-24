import sys
from typing import AsyncIterator, Callable, List, Mapping, Optional, Tuple

import httpcore

try:
    from contextlib import asynccontextmanager  # type: ignore  # Python 3.6.
except ImportError:  # pragma: no cover  # Python 3.6.
    from async_generator import asynccontextmanager  # type: ignore


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
        try:
            import anyio  # noqa
        except ImportError:  # pragma: no cover
            raise ImportError("ASGITransport requires anyio. (Hint: pip install anyio)")

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
        timeout: Mapping[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream]:

        headers = [] if headers is None else headers
        stream = httpcore.PlainByteStream(content=b"") if stream is None else stream

        app_context = run_asgi(
            self.app,
            method,
            url,
            headers,
            stream,
            client=self.client,
            root_path=self.root_path,
        )

        status_code, response_headers, response_body = await app_context.__aenter__()

        async def aclose() -> None:
            await app_context.__aexit__(*sys.exc_info())

        stream = httpcore.AsyncIteratorByteStream(response_body, aclose_func=aclose)

        return (b"HTTP/1.1", status_code, b"", response_headers, stream)


@asynccontextmanager
async def run_asgi(
    app: Callable,
    method: bytes,
    url: Tuple[bytes, bytes, Optional[int], bytes],
    headers: List[Tuple[bytes, bytes]],
    stream: httpcore.AsyncByteStream,
    *,
    client: str,
    root_path: str,
) -> AsyncIterator[Tuple[int, List[Tuple[bytes, bytes]], AsyncIterator[bytes]]]:
    import anyio

    # ASGI scope.
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
        "client": client,
        "root_path": root_path,
    }

    # Request.
    request_body_chunks = stream.__aiter__()
    request_complete = False

    # Response.
    status_code: Optional[int] = None
    response_headers: Optional[List[Tuple[bytes, bytes]]] = None
    response_body_queue = anyio.create_queue(1)
    response_started = anyio.create_event()
    response_complete = anyio.create_event()

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
        else:
            return {"type": "http.request", "body": body, "more_body": True}

    async def send(message: dict) -> None:
        nonlocal status_code, response_headers

        if message["type"] == "http.response.start":
            assert not response_started.is_set()
            status_code = message["status"]
            response_headers = message.get("headers", [])
            await response_started.set()

        elif message["type"] == "http.response.body":
            assert not response_complete.is_set()
            body = message.get("body", b"")
            more_body = message.get("more_body", False)

            if body and method != b"HEAD":
                await response_body_queue.put(body)

            if not more_body:
                await response_body_queue.put(None)
                await response_complete.set()

    async def body_iterator() -> AsyncIterator[bytes]:
        while True:
            chunk = await response_body_queue.get()
            if chunk is None:
                break
            yield chunk

    async with anyio.create_task_group() as task_group:
        await task_group.spawn(app, scope, receive, send)

        await response_started.wait()

        assert status_code is not None
        assert response_headers is not None

        yield status_code, response_headers, body_iterator()
