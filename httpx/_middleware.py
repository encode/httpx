from typing import Awaitable, Callable

from ._models import Request, Response


class Middleware:
    def send(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        raise NotImplementedError  # pragma: no cover


class AsyncMiddleware:
    async def asend(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        raise NotImplementedError  # pragma: no cover
