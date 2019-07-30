import hashlib
import os
import time
import typing
from base64 import b64encode
from urllib.parse import urlparse

from ..models import AsyncRequest, AsyncResponse, StatusCode
from .base import BaseMiddleware


class HTTPBasicAuthMiddleware(BaseMiddleware):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        self.username = username
        self.password = password

    def process_request(self, request: AsyncRequest) -> AsyncRequest:
        request.headers["Authorization"] = self.build_auth_header()
        return request

    def build_auth_header(self) -> str:
        username, password = self.username, self.password

        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()
        return f"Basic {token}"
