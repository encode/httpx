import typing
from types import TracebackType

from .config import (
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from .models import Response


async def request(
    method: str,
    url: str,
    *,
    headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
    body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
    stream: bool = False,
    ssl: SSLConfig = DEFAULT_SSL_CONFIG,
    timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
) -> Response:
    async with PoolManager(ssl=ssl, timeout=timeout) as pool:
       return await pool.request(
           method=method, url=url, headers=headers, body=body, stream=stream
       )


class PoolManager:
    def __init__(
        self,
        *,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        self.ssl = ssl
        self.timeout = timeout
        self.limits = limits
        self.is_closed = False

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        stream: bool = False,
    ) -> Response:
        raise NotImplementedError()

    async def close(self) -> None:
        self.is_closed = True

    async def __aenter__(self) -> "PoolManager":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()
