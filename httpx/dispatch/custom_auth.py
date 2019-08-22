import typing

from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..models import AsyncRequest, AsyncResponse
from .base import AsyncDispatcher


class CustomAuthDispatcher(AsyncDispatcher):
    def __init__(
        self,
        next_dispatcher: AsyncDispatcher,
        auth_callable: typing.Callable[[AsyncRequest], AsyncRequest],
    ):
        self.next_dispatcher = next_dispatcher
        self.auth_callable = auth_callable

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        request = self.auth_callable(request)
        return await self.next_dispatcher.send(
            request, verify=verify, cert=cert, timeout=timeout
        )
