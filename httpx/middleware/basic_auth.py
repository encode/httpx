import typing
from base64 import b64encode

from ..models import AsyncRequest, AsyncResponse
from ..utils import to_bytes
from .base import BaseMiddleware


class BasicAuthMiddleware(BaseMiddleware):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        self.authorization_header = build_basic_auth_header(username, password)

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request.headers["Authorization"] = self.authorization_header
        return await get_response(request)


def build_basic_auth_header(
    username: typing.Union[str, bytes], password: typing.Union[str, bytes]
) -> str:
    userpass = b":".join((to_bytes(username), to_bytes(password)))
    token = b64encode(userpass).decode().strip()
    return f"Basic {token}"
