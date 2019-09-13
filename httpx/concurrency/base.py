import ssl
import typing
from types import TracebackType

from ..config import PoolLimits, TimeoutConfig
from ..exceptions import ReadTimeout, WriteTimeout


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


class BaseTCPStream:
    """
    A TCP stream with read/write operations. Abstracts away any asyncio-specific
    interfaces into a more generic base class, that we can use with alternate
    backends, or for stand-alone test cases.
    """

    def __init__(self, timeout: TimeoutConfig):
        self.timeout = timeout
        self.write_buffer = b""

    def get_http_version(self) -> str:
        raise NotImplementedError()  # pragma: no cover

    async def read_or_timeout(self, n: int, timeout: typing.Optional[float]) -> bytes:
        raise NotImplementedError()  # pragma: no cover

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: typing.Any = None
    ) -> bytes:
        if timeout is None:
            timeout = self.timeout

        while True:
            # Check our flag at the first possible moment, and use a fine
            # grained retry loop if we're not yet in read-timeout mode.
            should_raise = flag is None or flag.raise_on_read_timeout
            read_timeout = timeout.read_timeout if should_raise else 0.01
            try:
                data = await self.read_or_timeout(n, read_timeout)
                break
            except ReadTimeout:
                if should_raise:
                    raise

        return data

    def write_no_block(self, data: bytes) -> None:
        self.write_buffer += data

    async def write_or_timeout(
        self, data: bytes, timeout: typing.Optional[float]
    ) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        if self.write_buffer:
            write_buffer = self.write_buffer
            # Reset write buffer before recursive call,
            # otherwise we'd go through this branch indefinitely.
            self.write_buffer = b""
            try:
                await self.write(write_buffer, timeout=timeout, flag=flag)
            except WriteTimeout:
                self.writer_buffer = write_buffer
                raise

        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        while True:
            try:
                await self.write_or_timeout(data, timeout.write_timeout)
                break
            except WriteTimeout:
                # We check our flag at the first possible moment, in order to
                # allow us to suppress write timeouts, if we've since
                # switched over to read-timeout mode.
                should_raise = flag is None or flag.raise_on_write_timeout
                if should_raise:
                    raise

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def is_connection_dropped(self) -> bool:
        raise NotImplementedError()  # pragma: no cover


class BaseQueue:
    """
    A FIFO queue. Abstracts away any asyncio-specific interfaces.
    """

    async def get(self) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    async def put(self, value: typing.Any) -> None:
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

    async def acquire(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def release(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class ConcurrencyBackend:
    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseTCPStream:
        raise NotImplementedError()  # pragma: no cover

    async def start_tls(
        self,
        stream: BaseTCPStream,
        hostname: str,
        ssl_context: ssl.SSLContext,
        timeout: TimeoutConfig,
    ) -> BaseTCPStream:
        raise NotImplementedError()  # pragma: no cover

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        raise NotImplementedError()  # pragma: no cover

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    async def iterate_in_threadpool(self, iterator):  # type: ignore
        class IterationComplete(Exception):
            pass

        def next_wrapper(iterator):  # type: ignore
            try:
                return next(iterator)
            except StopIteration:
                raise IterationComplete()

        while True:
            try:
                yield await self.run_in_threadpool(next_wrapper, iterator)
            except IterationComplete:
                break

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    def iterate(self, async_iterator):  # type: ignore
        while True:
            try:
                yield self.run(async_iterator.__anext__)
            except StopAsyncIteration:
                break

    def create_queue(self, max_size: int) -> BaseQueue:
        raise NotImplementedError()  # pragma: no cover

    def create_event(self) -> BaseEvent:
        raise NotImplementedError()  # pragma: no cover

    def background_manager(
        self, coroutine: typing.Callable, *args: typing.Any
    ) -> "BaseBackgroundManager":
        raise NotImplementedError()  # pragma: no cover


class BaseBackgroundManager:
    async def __aenter__(self) -> "BaseBackgroundManager":
        raise NotImplementedError()  # pragma: no cover

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self, exception: BaseException = None) -> None:
        if exception is None:
            await self.__aexit__(None, None, None)
        else:
            traceback = exception.__traceback__  # type: ignore
            await self.__aexit__(type(exception), exception, traceback)
