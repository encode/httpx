import typing

from ..models import AsyncRequest, AsyncResponse
from .base import BaseMiddleware


class CustomAuthMiddleware(BaseMiddleware):
    def __init__(self, auth: typing.Callable[[AsyncRequest], AsyncRequest]):
        self.auth = auth

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request = self.auth(request)
        return await get_response(request)
