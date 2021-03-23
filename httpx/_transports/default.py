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
from .base import AsyncBaseTransport, BaseTransport

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


def ensure_http_version_reason_phrase_as_bytes(extensions: dict) -> None:
    # From HTTPX 0.18 onwards we're treating the "reason_phrase" and "http_version"
    # extensions as bytes, in order to be more precise. Also we're using the
    # "reason_phrase" key in preference to "reason", in order to match properly
    # with the HTTP spec naming.
    # HTTPCore 0.12 does not yet use these same conventions for the extensions,
    # so we bridge between the two styles for now.
    if "reason" in extensions:
        extensions["reason_phrase"] = extensions.pop("reason").encode("ascii")
    if "http_version" in extensions:
        extensions["http_version"] = extensions["http_version"].encode("ascii")


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


class HTTPTransport(BaseTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
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
        self._pool.__exit__(exc_type, exc_value, traceback)

    def handle_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: typing.Iterator[bytes],
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], typing.Iterator[bytes], dict
    ]:
        with map_httpcore_exceptions():
            status_code, headers, byte_stream, extensions = self._pool.request(
                method=method,
                url=url,
                headers=headers,
                stream=stream,  # type: ignore
                ext=extensions,
            )

        def response_stream() -> typing.Iterator[bytes]:
            with map_httpcore_exceptions():
                for part in byte_stream:
                    yield part

        def close() -> None:
            with map_httpcore_exceptions():
                byte_stream.close()

        ensure_http_version_reason_phrase_as_bytes(extensions)
        extensions["close"] = close

        return status_code, headers, response_stream(), extensions

    def close(self) -> None:
        self._pool.close()


class AsyncHTTPTransport(AsyncBaseTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
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
        await self._pool.__aexit__(exc_type, exc_value, traceback)

    async def handle_async_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: typing.AsyncIterator[bytes],
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], typing.AsyncIterator[bytes], dict
    ]:
        with map_httpcore_exceptions():
            status_code, headers, byte_stream, extenstions = await self._pool.arequest(
                method=method,
                url=url,
                headers=headers,
                stream=stream,  # type: ignore
                ext=extensions,
            )

        async def response_stream() -> typing.AsyncIterator[bytes]:
            with map_httpcore_exceptions():
                async for part in byte_stream:
                    yield part

        async def aclose() -> None:
            with map_httpcore_exceptions():
                await byte_stream.aclose()

        ensure_http_version_reason_phrase_as_bytes(extensions)
        extensions["aclose"] = aclose

        return status_code, headers, response_stream(), extensions

    async def aclose(self) -> None:
        await self._pool.aclose()
