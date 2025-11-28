from __future__ import annotations

import typing
from datetime import timedelta

from .._models import Request, Response
from .base import AsyncBaseTransport, BaseTransport

SyncHandler = typing.Callable[[Request], Response]
AsyncHandler = typing.Callable[[Request], typing.Coroutine[None, None, Response]]


__all__ = ["MockTransport"]


class MockTransport(AsyncBaseTransport, BaseTransport):
    def __init__(
        self, handler: SyncHandler | AsyncHandler, delay: timedelta = timedelta(0)
    ) -> None:
        self.handler = handler
        self.delay = delay

    def handle_request(
        self,
        request: Request,
    ) -> Response:
        request.read()
        response = self.handler(request)
        if not isinstance(response, Response):  # pragma: no cover
            raise TypeError("Cannot use an async handler in a sync Client")

        self._apply_elapsed(response)
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

        self._apply_elapsed(response)
        return response

    def _apply_elapsed(self, response: Response) -> None:
        # If the handler already set `response._elapsed`, it is preserved.
        # If a delay was provided to MockTransport, `.elapsed` is set to that duration.
        # If no delay is provided, `.elapsed` is explicitly set to None.
        if hasattr(response, "_elapsed"):
            return

        response._elapsed = self.delay
