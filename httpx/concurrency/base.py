import ssl
import typing

from ..config import Timeout


def lookup_backend(
    backend: typing.Union[str, "ConcurrencyBackend"] = "auto"
) -> "ConcurrencyBackend":
    if not isinstance(backend, str):
        return backend

    if backend == "auto":
        from .auto import AutoBackend

        return AutoBackend()
    elif backend == "asyncio":
        from .asyncio import AsyncioBackend

        return AsyncioBackend()
    elif backend == "trio":
        from .trio import TrioBackend

        return TrioBackend()

    raise RuntimeError(f"Unknown or unsupported concurrency backend {backend!r}")


class BaseSocketStream:
    """
    A socket stream with read/write operations. Abstracts away any asyncio-specific
    interfaces into a more generic base class, that we can use with alternate
    backends, or for stand-alone test cases.
    """

    def get_http_version(self) -> str:
        raise NotImplementedError()  # pragma: no cover

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: Timeout
    ) -> "BaseSocketStream":
        raise NotImplementedError()  # pragma: no cover

    async def read(self, n: int, timeout: Timeout) -> bytes:
        raise NotImplementedError()  # pragma: no cover

    async def write(self, data: bytes, timeout: Timeout) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def is_connection_dropped(self) -> bool:
        raise NotImplementedError()  # pragma: no cover


class BaseEvent:
    """
    An event object. Abstracts away any asyncio-specific interfaces.
    """

    def set(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def wait(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class BasePoolSemaphore:
    """
    A semaphore for use with connection pooling.

    Abstracts away any asyncio-specific interfaces.
    """

    async def acquire(self, timeout: float = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    def release(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class ConcurrencyBackend:
    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> BaseSocketStream:
        raise NotImplementedError()  # pragma: no cover

    async def open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> BaseSocketStream:
        raise NotImplementedError()  # pragma: no cover

    def time(self) -> float:
        raise NotImplementedError()  # pragma: no cover

    def get_semaphore(self, max_value: int) -> BasePoolSemaphore:
        raise NotImplementedError()  # pragma: no cover

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    def create_event(self) -> BaseEvent:
        raise NotImplementedError()  # pragma: no cover
