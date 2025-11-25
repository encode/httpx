from __future__ import annotations

import typing

from .._models import Request, Response
from .base import AsyncBaseTransport, BaseTransport
from datetime import timedelta

SyncHandler = typing.Callable[[Request], Response]
AsyncHandler = typing.Callable[[Request], typing.Coroutine[None, None, Response]]


__all__ = ["MockTransport"]


class MockTransport(AsyncBaseTransport, BaseTransport):
    def __init__(self, handler: SyncHandler | AsyncHandler, duration: float | None = None) -> None:
        self.handler = handler
        self.duration = duration

    def handle_request(
        self,
        request: Request,
    ) -> Response:
        request.read()
        response = self.handler(request)
        if not isinstance(response, Response):  # pragma: no cover
            raise TypeError("Cannot use an async handler in a sync Client")

        self.__apply_elapsed(response)
        return response

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        await request.aread()
        response = self.handler(request)

        # Allow handler to *optionally* be an `async` function.
        # If it is, then the `response` variable need to be awaited to actually
        # return the result.

        if not isinstance(response, Response):
            response = await response

        self.__apply_elapsed(response)
        return response

    def __apply_elapsed(self, response: Response) -> None:
        if self.duration is not None:
            response.elapsed = timedelta(seconds=self.duration)
        