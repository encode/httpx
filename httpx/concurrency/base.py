import ssl
import typing

from ..config import PoolLimits, TimeoutConfig


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
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: TimeoutConfig
    ) -> "BaseSocketStream":
        raise NotImplementedError()  # pragma: no cover

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> bytes:
        raise NotImplementedError()  # pragma: no cover

    def write_no_block(self, data: bytes) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        raise NotImplementedError()  # pragma: no cover

    def build_writer_reader_pair(
        self,
        chunk_size: int,
        produce_bytes: typing.Callable[[], typing.Awaitable[typing.Optional[bytes]]],
        consume_bytes: typing.Callable[[bytes], typing.Awaitable[None]],
        timeout: TimeoutConfig = None,
        flag: TimeoutFlag = None,
    ) -> typing.Tuple[typing.Callable, typing.Callable]:
        """
        Return the following pair of async functions:

        * Writer: writes bytes yielded by `produce_bytes()` to the network.
        * Reader: read bytes from the network in chunks, and pass them
        to `consume_bytes()`.
        """

        async def writer() -> None:
            while True:
                outgoing = await produce_bytes()
                if outgoing is None:
                    return
                await self.write(outgoing, timeout=timeout, flag=flag)

        async def reader() -> None:
            while True:
                incoming = await self.read(chunk_size, timeout=timeout, flag=flag)
                await consume_bytes(incoming)

        return writer, reader

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
    ) -> BaseSocketStream:
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

    async def run_concurrently(
        self, *coroutines: typing.Callable[[], typing.Awaitable[None]],
    ) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def start_in_background(
        self, coroutine: typing.Callable
    ) -> typing.Callable[[typing.Optional[BaseException]], typing.Awaitable[None]]:
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
