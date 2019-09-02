import typing

from ..models import AsyncRequest, AsyncResponse


class BaseMiddleware:
    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        raise NotImplementedError  # pragma: no cover
