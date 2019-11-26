import typing
from base64 import b64encode

from .models import Request, Response
from .utils import to_bytes


class BasicAuth:
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        self.auth_header = self.build_auth_header(username, password)

    def __call__(self, request: Request) -> Request:
        request.headers["Authorization"] = self.auth_header
        return request

    def build_auth_header(self,
        username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> str:
        userpass = b":".join((to_bytes(username), to_bytes(password)))
        token = b64encode(userpass).decode().strip()
        return f"Basic {token}"
