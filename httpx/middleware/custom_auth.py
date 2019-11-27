import typing

from ..models import Request, Response
from .base import BaseMiddleware


class CustomAuthMiddleware(BaseMiddleware):
    def __init__(self, auth: typing.Callable[[Request], Request]):
        self.auth = auth

    async def __call__(
        self, request: Request, get_response: typing.Callable
    ) -> Response:
        request = self.auth(request)
        return await get_response(request)
