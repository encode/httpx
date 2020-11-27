"""
Custom transports, with nicely configured defaults.

The following additional keyword arguments are currently supported by httpcore...

* uds: str
* local_address: str
* retries: int
* backend: str ("auto", "asyncio", "trio", "curio", "anyio", "sync")

Example usages...

# Disable HTTP/2 on a single specfic domain.
mounts = {
    "all://": httpx.HTTPTransport(http2=True),
    "all://*example.org": httpx.HTTPTransport()
}

# Using advanced httpcore configuration, with connection retries.
transport = httpx.HTTPTransport(retries=1)
client = httpx.Client(transport=transport)

# Using advanced httpcore configuration, with unix domain sockets.
transport = httpx.HTTPTransport(uds="socket.uds")
client = httpx.Client(transport=transport)
"""
import typing
from types import TracebackType

import httpcore

from .._config import DEFAULT_LIMITS, Limits, create_ssl_context
from .._types import CertTypes, VerifyTypes

T = typing.TypeVar("T")
Headers = typing.List[typing.Tuple[bytes, bytes]]
URL = typing.Tuple[bytes, bytes, typing.Optional[int], bytes]


class HTTPTransport(httpcore.SyncHTTPTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        self._pool = httpcore.SyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=limits.keepalive_expiry,
            http2=http2,
            **kwargs,
        )

    def __enter__(self: T) -> T:
        return self._pool.__enter__()  # type: ignore

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self._pool.__exit__()

    def request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: httpcore.SyncByteStream = None,
        ext: dict = None,
    ) -> typing.Tuple[int, Headers, httpcore.SyncByteStream, dict]:
        return self._pool.request(method, url, headers=headers, stream=stream, ext=ext)

    def close(self) -> None:
        self._pool.close()


class AsyncHTTPTransport(httpcore.AsyncHTTPTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=limits.keepalive_expiry,
            http2=http2,
            **kwargs,
        )

    async def __aenter__(self: T) -> T:
        return await self._pool.__aenter__()  # type: ignore

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self._pool.__aexit__()

    async def arequest(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: httpcore.AsyncByteStream = None,
        ext: dict = None,
    ) -> typing.Tuple[int, Headers, httpcore.AsyncByteStream, dict]:
        return await self._pool.arequest(
            method, url, headers=headers, stream=stream, ext=ext
        )

    async def aclose(self) -> None:
        await self._pool.aclose()
