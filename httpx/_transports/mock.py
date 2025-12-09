from __future__ import annotations

import datetime
import typing

from .._models import Request, Response
from .base import AsyncBaseTransport, BaseTransport

SyncHandler = typing.Callable[[Request], Response]
AsyncHandler = typing.Callable[[Request], typing.Coroutine[None, None, Response]]


__all__ = ["MockTransport"]


class MockTransport(AsyncBaseTransport, BaseTransport):
    def __init__(self, handler: SyncHandler | AsyncHandler) -> None:
        self.handler = handler

    def handle_request(
        self,
        request: Request,
    ) -> Response:
        request.read()
        response = self.handler(request)
        if not isinstance(response, Response):  # pragma: no cover
            raise TypeError("Cannot use an async handler in a sync Client")
        if not hasattr(response, "_elapsed"):
            response.elapsed = datetime.timedelta(0)
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

        if not hasattr(response, "_elapsed"):
            response.elapsed = datetime.timedelta(0)
        return response
