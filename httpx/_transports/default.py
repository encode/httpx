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
import contextlib
import typing
from types import TracebackType

import httpcore

from .._config import DEFAULT_LIMITS, Limits, Proxy, create_ssl_context
from .._exceptions import (
    CloseError,
    ConnectError,
    ConnectTimeout,
    LocalProtocolError,
    NetworkError,
    PoolTimeout,
    ProtocolError,
    ProxyError,
    ReadError,
    ReadTimeout,
    RemoteProtocolError,
    TimeoutException,
    UnsupportedProtocol,
    WriteError,
    WriteTimeout,
)
from .._types import CertTypes, VerifyTypes
from .base import AsyncBaseTransport, AsyncByteStream, BaseTransport, SyncByteStream

T = typing.TypeVar("T", bound="HTTPTransport")
A = typing.TypeVar("A", bound="AsyncHTTPTransport")


@contextlib.contextmanager
def map_httpcore_exceptions() -> typing.Iterator[None]:
    try:
        yield
    except Exception as exc:
        mapped_exc = None

        for from_exc, to_exc in HTTPCORE_EXC_MAP.items():
            if not isinstance(exc, from_exc):
                continue
            # We want to map to the most specific exception we can find.
            # Eg if `exc` is an `httpcore.ReadTimeout`, we want to map to
            # `httpx.ReadTimeout`, not just `httpx.TimeoutException`.
            if mapped_exc is None or issubclass(to_exc, mapped_exc):
                mapped_exc = to_exc

        if mapped_exc is None:  # pragma: nocover
            raise

        message = str(exc)
        raise mapped_exc(message) from exc


HTTPCORE_EXC_MAP = {
    httpcore.TimeoutException: TimeoutException,
    httpcore.ConnectTimeout: ConnectTimeout,
    httpcore.ReadTimeout: ReadTimeout,
    httpcore.WriteTimeout: WriteTimeout,
    httpcore.PoolTimeout: PoolTimeout,
    httpcore.NetworkError: NetworkError,
    httpcore.ConnectError: ConnectError,
    httpcore.ReadError: ReadError,
    httpcore.WriteError: WriteError,
    httpcore.CloseError: CloseError,
    httpcore.ProxyError: ProxyError,
    httpcore.UnsupportedProtocol: UnsupportedProtocol,
    httpcore.ProtocolError: ProtocolError,
    httpcore.LocalProtocolError: LocalProtocolError,
    httpcore.RemoteProtocolError: RemoteProtocolError,
}


class ResponseStream(SyncByteStream):
    def __init__(self, httpcore_stream: httpcore.SyncByteStream):
        self._httpcore_stream = httpcore_stream

    def __iter__(self) -> typing.Iterator[bytes]:
        with map_httpcore_exceptions():
            for part in self._httpcore_stream:
                yield part

    def close(self) -> None:
        with map_httpcore_exceptions():
            self._httpcore_stream.close()


class HTTPTransport(BaseTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        proxy: Proxy = None,
        uds: str = None,
        local_address: str = None,
        retries: int = 0,
        backend: str = "sync",
    ) -> None:
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        if proxy is None:
            self._pool = httpcore.SyncConnectionPool(
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                uds=uds,
                local_address=local_address,
                retries=retries,
                backend=backend,
            )
        else:
            self._pool = httpcore.SyncHTTPProxy(
                proxy_url=proxy.url.raw,
                proxy_headers=proxy.headers.raw,
                proxy_mode=proxy.mode,
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http2=http2,
                backend=backend,
            )

    def __enter__(self: T) -> T:  # Use generics for subclass support.
        self._pool.__enter__()
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        with map_httpcore_exceptions():
            self._pool.__exit__(exc_type, exc_value, traceback)

    def handle_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: SyncByteStream,
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], SyncByteStream, dict
    ]:
        with map_httpcore_exceptions():
            status_code, headers, byte_stream, extensions = self._pool.handle_request(
                method=method,
                url=url,
                headers=headers,
                stream=httpcore.IteratorByteStream(iter(stream)),
                extensions=extensions,
            )

        stream = ResponseStream(byte_stream)

        return status_code, headers, stream, extensions

    def close(self) -> None:
        self._pool.close()


class AsyncResponseStream(AsyncByteStream):
    def __init__(self, httpcore_stream: httpcore.AsyncByteStream):
        self._httpcore_stream = httpcore_stream

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        with map_httpcore_exceptions():
            async for part in self._httpcore_stream:
                yield part

    async def aclose(self) -> None:
        with map_httpcore_exceptions():
            await self._httpcore_stream.aclose()


class AsyncHTTPTransport(AsyncBaseTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        proxy: Proxy = None,
        uds: str = None,
        local_address: str = None,
        retries: int = 0,
        backend: str = "auto",
    ) -> None:
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        if proxy is None:
            self._pool = httpcore.AsyncConnectionPool(
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                uds=uds,
                local_address=local_address,
                retries=retries,
                backend=backend,
            )
        else:
            self._pool = httpcore.AsyncHTTPProxy(
                proxy_url=proxy.url.raw,
                proxy_headers=proxy.headers.raw,
                proxy_mode=proxy.mode,
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http2=http2,
                backend=backend,
            )

    async def __aenter__(self: A) -> A:  # Use generics for subclass support.
        await self._pool.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        with map_httpcore_exceptions():
            await self._pool.__aexit__(exc_type, exc_value, traceback)

    async def handle_async_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: AsyncByteStream,
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], AsyncByteStream, dict
    ]:
        with map_httpcore_exceptions():
            (
                status_code,
                headers,
                byte_stream,
                extensions,
            ) = await self._pool.handle_async_request(
                method=method,
                url=url,
                headers=headers,
                stream=httpcore.AsyncIteratorByteStream(stream.__aiter__()),
                extensions=extensions,
            )

        stream = AsyncResponseStream(byte_stream)

        return status_code, headers, stream, extensions

    async def aclose(self) -> None:
        await self._pool.aclose()
