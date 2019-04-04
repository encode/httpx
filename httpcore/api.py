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
from .exceptions import ResponseClosed, StreamConsumed


async def request(
    method: str,
    url: str,
    *,
    headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
    body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
    stream: bool = False,
    ssl: SSLConfig = DEFAULT_SSL_CONFIG,
    timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
) -> "Response":
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
    ) -> "Response":
        if stream:
            async def streaming_body():
                yield b"Hello, "
                yield b"world!"
            return Response(200, body=streaming_body)
        return Response(200, body=b"Hello, world!")

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


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        on_close: typing.Callable = None,
    ):
        self.status_code = status_code
        self.headers = list(headers)
        self.on_close = on_close
        self.is_closed = False
        self.is_streamed = False
        if isinstance(body, bytes):
            self.is_closed = True
            self.body = body
        else:
            self.body_aiter = body

    async def read(self) -> bytes:
        if not hasattr(self, "body"):
            body = b""
            async for part in self.stream():
                body += part
            self.body = body
        return self.body

    async def stream(self) -> typing.AsyncIterator[bytes]:
        if hasattr(self, "body"):
            yield self.body
        else:
            if self.is_streamed:
                raise StreamConsumed()
            if self.is_closed:
                raise ResponseClosed()
            self.is_streamed = True
            async for part in self.body_aiter():
                yield part
            await self.close()

    async def close(self) -> None:
        if not self.is_closed:
            self.is_closed = True
            if self.on_close is not None:
                await self.on_close()

    async def __aenter__(self) -> "Response":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        if not self.is_closed:
            await self.close()
