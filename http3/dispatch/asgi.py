import asyncio
import typing

from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import AsyncDispatcher
from ..models import AsyncRequest, AsyncResponse


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

        scope = {"method": request.method}
        status_code = None
        headers = None
        complete = asyncio.Event()
        body_messages = asyncio.Queue(
            maxsize=3
        )  # type: asyncio.Queue[typing.Optional[bytes]]
        request_stream = request.stream()

        async def receive() -> dict:
            nonlocal request_stream

            try:
                body = await request_stream.__anext__()
            except StopAsyncIteration:
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: dict) -> None:
            nonlocal complete, status_code, headers

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.get("headers", [])
                complete.set()
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if body:
                    await body_messages.put(body)
                if not more_body:
                    await body_messages.put(None)

        loop = asyncio.get_event_loop()
        run_app = loop.create_task(self.app(scope, receive, send))
        wait_response = loop.create_task(complete.wait())

        await asyncio.wait(
            {run_app, wait_response}, return_when=asyncio.FIRST_COMPLETED
        )

        assert complete.is_set, "application did not return a response."
        assert status_code is not None
        assert headers is not None

        async def on_close() -> None:
            nonlocal run_app
            await run_app

        return AsyncResponse(
            status_code=status_code,
            protocol="HTTP/1.1",
            headers=headers,
            content=self.response_content(body_messages),
            on_close=on_close,
            request=request,
        )

    async def response_content(
        self, queue: asyncio.Queue
    ) -> typing.AsyncIterator[bytes]:
        while True:
            body = await queue.get()
            if body is None:
                break
            yield body
