import ssl
import typing

from ..config import PoolLimits, Timeout


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


class TimeoutFlag:
    """
    A timeout flag holds a state of either read-timeout or write-timeout mode.

    We use this so that we can attempt both reads and writes concurrently, while
    only enforcing timeouts in one direction.

    During a request/response cycle we start in write-timeout mode.

    Once we've sent a request fully, or once we start seeing a response,
    then we switch to read-timeout mode instead.
    """

    def __init__(self) -> None:
        self.raise_on_read_timeout = False
        self.raise_on_write_timeout = True

    def set_read_timeouts(self) -> None:
        """
        Set the flag to read-timeout mode.
        """
        self.raise_on_read_timeout = True
        self.raise_on_write_timeout = False

    def set_write_timeouts(self) -> None:
        """
        Set the flag to write-timeout mode.
        """
        self.raise_on_read_timeout = False
        self.raise_on_write_timeout = True


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

    async def read(self, n: int, timeout: Timeout, flag: typing.Any = None) -> bytes:
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

    def is_set(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def clear(self) -> None:
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

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
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

    async def fork(
        self,
        coroutine1: typing.Callable,
        args1: typing.Sequence,
        coroutine2: typing.Callable,
        args2: typing.Sequence,
    ) -> None:
        """
        Run two coroutines concurrently.

        This should start 'coroutine1' with '*args1' and 'coroutine2' with '*args2',
        and wait for them to finish.

        In case one of the coroutines raises an exception, cancel the other one then
        raise. If the other coroutine had also raised an exception, ignore it.
        """
        raise NotImplementedError()  # pragma: no cover
