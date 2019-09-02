import typing
from base64 import b64encode

from .base import BaseMiddleware
from ..models import AsyncRequest, AsyncResponse


class BasicAuthMiddleware(BaseMiddleware):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()

        self.authorization_header = f"Basic {token}"

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request.headers["Authorization"] = self.authorization_header
        return await get_response(request)


class CustomAuthMiddleware(BaseMiddleware):
    def __init__(self, auth: typing.Callable[[AsyncRequest], AsyncRequest]):
        self.auth = auth

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request = self.auth(request)
        return await get_response(request)
