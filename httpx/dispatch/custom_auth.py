from base64 import b64encode
import typing

from .base import AsyncDispatcher
from ..concurrency.base import ConcurrencyBackend
from .connection import ReleaseCallback
from ..models import (
    AsyncRequest,
    AsyncResponse,
    AuthTypes,
    URL,
    Headers,
    Cookies,
    Origin,
)
from ..config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    PoolLimits,
    TimeoutTypes,
    VerifyTypes,
    HTTPVersionTypes,
)


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
