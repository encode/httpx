import typing
from base64 import b64encode

from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..models import AsyncRequest, AsyncResponse
from .base import AsyncDispatcher


class BasicAuthDispatcher(AsyncDispatcher):
    def __init__(
        self,
        next_dispatcher: AsyncDispatcher,
        username: typing.Union[str, bytes],
        password: typing.Union[str, bytes],
    ):
        self.next_dispatcher = next_dispatcher
        self.username = username
        self.password = password

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        request.headers["Authorization"] = self.build_auth_header()
        return await self.next_dispatcher.send(
            request, verify=verify, cert=cert, timeout=timeout
        )

    def build_auth_header(self) -> str:
        username, password = self.username, self.password

        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()
        return f"Basic {token}"
