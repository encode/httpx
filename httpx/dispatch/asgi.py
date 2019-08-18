import asyncio
import typing

from ..concurrency.asyncio import AsyncioBackend
from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import AsyncDispatcher, ConcurrencyBackend
from ..models import AsyncRequest, AsyncResponse


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
        backend: ConcurrencyBackend = None,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: typing.Tuple[str, int] = ("127.0.0.1", 123),
    ) -> None:
        self.app = app
        self.backend = AsyncioBackend() if backend is None else backend
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client

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
        response_started = self.backend.create_event()
        response_body = self.backend.body_iterator()
        request_stream = request.stream()

        async def receive() -> dict:
            nonlocal request_stream

            try:
                body = await request_stream.__anext__()
            except StopAsyncIteration:
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: dict) -> None:
            nonlocal status_code, headers, response_started, response_body, request

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.get("headers", [])
                response_started.set()
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if body and request.method != "HEAD":
                    await response_body.put(body)
                if not more_body:
                    await response_body.done()

        async def run_app() -> None:
            nonlocal app, scope, receive, send, app_exc, response_body
            try:
                await app(scope, receive, send)
            except Exception as exc:
                app_exc = exc
            finally:
                await response_body.done()

        # Really we'd like to push all `asyncio` logic into concurrency.py,
        # with a standardized interface, so that we can support other event
        # loop implementations, such as Trio and Curio.
        # That's a bit fiddly here, so we're not yet supporting using a custom
        # `ConcurrencyBackend` with the `Client(app=asgi_app)` case.
        loop = asyncio.get_event_loop()
        app_task = loop.create_task(run_app())
        response_task = loop.create_task(response_started.wait())

        tasks = {app_task, response_task}  # type: typing.Set[asyncio.Task]

        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        if app_exc is not None and self.raise_app_exceptions:
            raise app_exc

        assert response_started.is_set(), "application did not return a response."
        assert status_code is not None
        assert headers is not None

        async def on_close() -> None:
            nonlocal app_task, response_body
            await response_body.drain()
            await app_task
            if app_exc is not None and self.raise_app_exceptions:
                raise app_exc

        return AsyncResponse(
            status_code=status_code,
            protocol="HTTP/1.1",
            headers=headers,
            content=response_body.iterate(),
            on_close=on_close,
            request=request,
        )
