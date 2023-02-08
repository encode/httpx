import asyncio
import typing

from .._models import Request, Response
from .base import AsyncBaseTransport, BaseTransport


SyncHandler = typing.Callable[[Request], Response]
AsyncHandler = typing.Callable[[Request], typing.Coroutine[None, None, Response]]


class MockTransport(AsyncBaseTransport, BaseTransport):
    def __init__(self, handler: typing.Union[SyncHandler, AsyncHandler]) -> None:
        self.handler = handler

    def handle_request(
        self,
        request: Request,
    ) -> Response:
        request.read()
        return self.handler(request)

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        await request.aread()
        response = self.handler(request)

        # Allow handler to *optionally* be an `async` function.
        # If it is, then the `response` variable need to be awaited to actually
        # return the result.

        # https://simonwillison.net/2020/Sep/2/await-me-maybe/
        if asyncio.iscoroutine(response):
            response = await response

        return response
