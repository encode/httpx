import typing

from ..concurrency.asyncio import AsyncioBackend
from ..concurrency.base import ConcurrencyBackend
from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..models import AsyncRequest, AsyncResponse
from .base import AsyncDispatcher


class ASGIDispatch(AsyncDispatcher):
    """
    A custom dispatcher that handles sending requests directly to an ASGI app.

    The simplest way to use this functionality is to use the `app`argument.
    This will automatically infer if 'app' is a WSGI or an ASGI application,
    and will setup an appropriate dispatch class:

    ```
    client = httpx.Client(app=app)
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
    client = httpx.Client(dispatch=dispatch)

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
        app: typing.Callable,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: typing.Tuple[str, int] = ("127.0.0.1", 123),
        backend: ConcurrencyBackend = None,
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client
        self.backend = AsyncioBackend() if backend is None else backend

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": request.headers.raw,
            "scheme": request.url.scheme,
            "path": request.url.path,
            "query_string": request.url.query.encode("ascii"),
            "server": request.url.host,
            "client": self.client,
            "root_path": self.root_path,
        }
        app = self.app
        app_exc = None
        status_code = None
        headers = None
        response_started_or_failed = self.backend.create_event()
        response_body = BodyIterator(self.backend)
        request_stream = request.stream()

        async def receive() -> dict:
            nonlocal request_stream

            try:
                body = await request_stream.__anext__()
            except StopAsyncIteration:
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: dict) -> None:
            nonlocal status_code, headers, response_started_or_failed
            nonlocal response_body, request

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.get("headers", [])
                response_started_or_failed.set()
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if body and request.method != "HEAD":
                    await response_body.put(body)
                if not more_body:
                    await response_body.mark_as_done()

        async def run_app() -> None:
            nonlocal app, scope, receive, send, app_exc, response_body
            try:
                await app(scope, receive, send)
            except Exception as exc:
                app_exc = exc
            finally:
                await response_body.mark_as_done()
                response_started_or_failed.set()

        # Using the background manager here *works*, but it is weak design because
        # the background task isn't strictly context-managed.
        # We could consider refactoring the other uses of this abstraction
        # (mainly sending/receiving request/response data in h11 and h2 dispatchers),
        # and see if that allows us to come back here and refactor things out.
        background = await self.backend.background_manager(run_app).__aenter__()

        await response_started_or_failed.wait()

        if app_exc is not None and self.raise_app_exceptions:
            raise app_exc

        assert status_code is not None, "application did not return a response."
        assert headers is not None

        async def on_close() -> None:
            nonlocal response_body
            await response_body.drain()
            await background.__aexit__(None, None, None)
            if app_exc is not None and self.raise_app_exceptions:
                raise app_exc

        return AsyncResponse(
            status_code=status_code,
            http_version="HTTP/1.1",
            headers=headers,
            content=response_body.iterate(),
            on_close=on_close,
            request=request,
        )


class BodyIterator:
    """
    Provides a byte-iterator interface that the client can use to
    ingest the response content from.
    """

    def __init__(self, backend: ConcurrencyBackend) -> None:
        self._queue = backend.create_queue(max_size=1)
        self._done = object()

    async def iterate(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator, used by the client to consume the response body.
        """
        while True:
            data = await self._queue.get()
            if data is self._done:
                break
            assert isinstance(data, bytes)
            yield data

    async def drain(self) -> None:
        """
        Drain any remaining body, in order to allow any blocked `put()` calls
        to complete.
        """
        async for chunk in self.iterate():
            pass  # pragma: no cover

    async def put(self, data: bytes) -> None:
        """
        Used by the server to add data to the response body.
        """
        await self._queue.put(data)

    async def mark_as_done(self) -> None:
        """
        Used by the server to signal the end of the response body.
        """
        await self._queue.put(self._done)
