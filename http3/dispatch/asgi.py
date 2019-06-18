import asyncio
import typing

from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import AsyncDispatcher
from ..models import AsyncRequest, AsyncResponse


class BodyIterator:
    def __init__(self) -> None:
        self._queue = asyncio.Queue(
            maxsize=1
        )  # type: asyncio.Queue[typing.Union[bytes, object]]
        self._done = object()

    async def iterate(self) -> typing.AsyncIterator[bytes]:
        while True:
            data = await self._queue.get()
            if data is self._done:
                break
            assert isinstance(data, bytes)
            yield data

    async def put(self, data: bytes) -> None:
        await self._queue.put(data)

    async def done(self) -> None:
        await self._queue.put(self._done)


class ASGIDispatch(AsyncDispatcher):
    def __init__(self, app: typing.Callable) -> None:
        self.app = app

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
            "method": request.method,
            "headers": request.headers.raw,
            "scheme": request.url.scheme,
            "path": request.url.path,
            "query": request.url.query.encode("ascii"),
            "server": request.url.host,
        }
        app = self.app
        app_exc = None
        status_code = None
        headers = None
        response_started = asyncio.Event()
        response_body = BodyIterator()
        request_stream = request.stream()

        async def receive() -> dict:
            nonlocal request_stream

            try:
                body = await request_stream.__anext__()
            except StopAsyncIteration:
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: dict) -> None:
            nonlocal status_code, headers, response_started, response_body

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.get("headers", [])
                response_started.set()
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if body:
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

        loop = asyncio.get_event_loop()
        app_task = loop.create_task(run_app())
        response_task = loop.create_task(response_started.wait())

        tasks = [app_task, response_task]

        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        if app_exc is not None:
            raise app_exc

        assert response_started.is_set, "application did not return a response."
        assert status_code is not None
        assert headers is not None

        async def on_close() -> None:
            nonlocal app_task
            await app_task
            if app_exc is not None:
                raise app_exc

        return AsyncResponse(
            status_code=status_code,
            protocol="HTTP/1.1",
            headers=headers,
            content=response_body.iterate(),
            on_close=on_close,
            request=request,
        )
