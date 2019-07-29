import json
import typing
from base64 import b64encode

from .models import AsyncRequest

try:
    import jwt
except ImportError:  # pragma: nocover
    jwt = None  # type: ignore


class AuthBase:
    """
    Base class that all auth implementations derive from.
    """

    def __call__(self, request: AsyncRequest) -> AsyncRequest:
        raise NotImplementedError("Auth hooks must be callable.")  # pragma: nocover


class HTTPBasicAuth(AuthBase):
    token: str = ""
    auth_type: str = ""

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        self.token = b64encode(userpass).decode().strip()
        self.auth_type = "Basic"

    def __call__(self, request: AsyncRequest) -> AsyncRequest:
        if not self.auth_type or not self.token:
            raise ValueError("auth_type and token must be set")  # pragma: nocover
        request.headers["Authorization"] = f"{self.auth_type} {self.token}"
        return request


class HTTPJwtBasicAuth(HTTPBasicAuth):
    def __init__(
        self,
        payload: typing.Union[str, dict],
        secret: str = "",
        algorithm: str = "HS256",
    ) -> None:
        assert (
            jwt is not None
        ), "The 'jwt' library must be installed to use 'HTTPJwtBasicAuth'"

        if isinstance(payload, str):
            payload = json.loads(payload)

        btoken = jwt.encode(payload, secret, algorithm=algorithm)  # type: ignore
        self.token = btoken.decode().strip()
        self.auth_type = "JWT"
