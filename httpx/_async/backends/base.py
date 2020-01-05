import ssl
import typing
from types import TracebackType

from ...config import Timeout
from ..unasync_utils import is_async_mode


def lookup_backend(
    backend: typing.Union[str, "AsyncConcurrencyBackend"] = "auto"
) -> "AsyncConcurrencyBackend":
    if not isinstance(backend, str):
        return backend

    if not is_async_mode():
        from ...backends.sync import SyncBackend

        return SyncBackend()  # type: ignore

    if backend == "auto":
        from ...backends.auto import AutoBackend

        return AutoBackend()  # type: ignore
    elif backend == "asyncio":
        from ...backends.asyncio import AsyncioBackend

        return AsyncioBackend()  # type: ignore
    elif backend == "trio":
        from ...backends.trio import TrioBackend

        return TrioBackend()  # type: ignore

    raise RuntimeError(f"Unknown or unsupported concurrency backend {backend!r}")


class AsyncBaseSocketStream:
    """
    A socket stream with read/write operations. Abstracts away any asyncio-specific
    interfaces into a more generic base class, that we can use with alternate
    backends, or for stand-alone test cases.
    """

    def get_http_version(self) -> str:
        raise NotImplementedError()  # pragma: no cover

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: Timeout
    ) -> "AsyncBaseSocketStream":
        raise NotImplementedError()  # pragma: no cover

    async def read(self, n: int, timeout: Timeout) -> bytes:
        raise NotImplementedError()  # pragma: no cover

    async def write(self, data: bytes, timeout: Timeout) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def is_connection_dropped(self) -> bool:
        raise NotImplementedError()  # pragma: no cover


class AsyncBaseLock:
    """
    An abstract interface for Lock classes.
    Abstracts away any asyncio-specific interfaces.
    """

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.release()

    def release(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def acquire(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class AsyncBaseSemaphore:
    """
    An abstract interface for Semaphore classes.
    Abstracts away any asyncio-specific interfaces.
    """

    async def acquire(self, timeout: float = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    def release(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class AsyncConcurrencyBackend:
    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> AsyncBaseSocketStream:
        raise NotImplementedError()  # pragma: no cover

    async def open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> AsyncBaseSocketStream:
        raise NotImplementedError()  # pragma: no cover

    def time(self) -> float:
        raise NotImplementedError()  # pragma: no cover

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    def create_semaphore(self, max_value: int, exc_class: type) -> AsyncBaseSemaphore:
        raise NotImplementedError()  # pragma: no cover

    def create_lock(self) -> AsyncBaseLock:
        raise NotImplementedError()  # pragma: no cover
