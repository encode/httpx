"""
The `Reader` and `Writer` classes here provide a lightweight layer over
`asyncio.StreamReader` and `asyncio.StreamWriter`.

Similarly `PoolSemaphore` is a lightweight layer over `BoundedSemaphore`.

These classes help encapsulate the timeout logic, make it easier to unit-test
protocols, and help keep the rest of the package more `async`/`await`
based, and less strictly `asyncio`-specific.
"""
import asyncio
import functools
import ssl
import typing
from types import TracebackType

from .config import DEFAULT_TIMEOUT_CONFIG, PoolLimits, TimeoutConfig
from .exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from .interfaces import (
    BaseBackgroundManager,
    BasePoolSemaphore,
    BaseReader,
    BaseWriter,
    ConcurrencyBackend,
    Protocol,
)

SSL_MONKEY_PATCH_APPLIED = False


def ssl_monkey_patch() -> None:
    """
    Monky-patch for https://bugs.python.org/issue36709

    This prevents console errors when outstanding HTTPS connections
    still exist at the point of exiting.

    Clients which have been opened using a `with` block, or which have
    had `close()` closed, will not exhibit this issue in the first place.
    """
    MonkeyPatch = asyncio.selector_events._SelectorSocketTransport  # type: ignore

    _write = MonkeyPatch.write

    def _fixed_write(self, data: bytes) -> None:  # type: ignore
        if self._loop and not self._loop.is_closed():
            _write(self, data)

    MonkeyPatch.write = _fixed_write


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


class Reader(BaseReader):
    def __init__(
        self, stream_reader: asyncio.StreamReader, timeout: TimeoutConfig
    ) -> None:
        self.stream_reader = stream_reader
        self.timeout = timeout

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> bytes:
        if timeout is None:
            timeout = self.timeout

        while True:
            # Check our flag at the first possible moment, and use a fine
            # grained retry loop if we're not yet in read-timeout mode.
            should_raise = flag is None or flag.raise_on_read_timeout
            read_timeout = timeout.read_timeout if should_raise else 0.01
            try:
                data = await asyncio.wait_for(self.stream_reader.read(n), read_timeout)
                break
            except asyncio.TimeoutError:
                if should_raise:
                    raise ReadTimeout() from None

        return data


class Writer(BaseWriter):
    def __init__(self, stream_writer: asyncio.StreamWriter, timeout: TimeoutConfig):
        self.stream_writer = stream_writer
        self.timeout = timeout

    def write_no_block(self, data: bytes) -> None:
        self.stream_writer.write(data)  # pragma: nocover

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        self.stream_writer.write(data)
        while True:
            try:
                await asyncio.wait_for(  # type: ignore
                    self.stream_writer.drain(), timeout.write_timeout
                )
                break
            except asyncio.TimeoutError:
                # We check our flag at the possible moment, in order to
                # allow us to suppress write timeouts, if we've since
                # switched over to read-timeout mode.
                should_raise = flag is None or flag.raise_on_write_timeout
                if should_raise:
                    raise WriteTimeout() from None

    async def close(self) -> None:
        self.stream_writer.close()


class PoolSemaphore(BasePoolSemaphore):
    def __init__(self, pool_limits: PoolLimits):
        self.pool_limits = pool_limits

    @property
    def semaphore(self) -> typing.Optional[asyncio.BoundedSemaphore]:
        if not hasattr(self, "_semaphore"):
            max_connections = self.pool_limits.hard_limit
            if max_connections is None:
                self._semaphore = None
            else:
                self._semaphore = asyncio.BoundedSemaphore(value=max_connections)
        return self._semaphore

    async def acquire(self) -> None:
        if self.semaphore is None:
            return

        timeout = self.pool_limits.pool_timeout
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout)
        except asyncio.TimeoutError:
            raise PoolTimeout()

    def release(self) -> None:
        if self.semaphore is None:
            return

        self.semaphore.release()


class AsyncioBackend(ConcurrencyBackend):
    def __init__(self) -> None:
        global SSL_MONKEY_PATCH_APPLIED

        if not SSL_MONKEY_PATCH_APPLIED:
            ssl_monkey_patch()
        SSL_MONKEY_PATCH_APPLIED = True

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not hasattr(self, "_loop"):
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
        return self._loop

    async def connect(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> typing.Tuple[BaseReader, BaseWriter, Protocol]:
        try:
            stream_reader, stream_writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(hostname, port, ssl=ssl_context),
                timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

        ssl_object = stream_writer.get_extra_info("ssl_object")
        if ssl_object is None:
            ident = "http/1.1"
        else:
            ident = ssl_object.selected_alpn_protocol()
            if ident is None:
                ident = ssl_object.selected_npn_protocol()

        reader = Reader(stream_reader=stream_reader, timeout=timeout)
        writer = Writer(stream_writer=stream_writer, timeout=timeout)
        protocol = Protocol.HTTP_2 if ident == "h2" else Protocol.HTTP_11

        return (reader, writer, protocol)

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        if kwargs:
            # loop.run_in_executor doesn't accept 'kwargs', so bind them in here
            func = functools.partial(func, **kwargs)
        return await self.loop.run_in_executor(None, func, *args)

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        loop = self.loop
        if loop.is_running():
            self._loop = asyncio.new_event_loop()
        try:
            return self.loop.run_until_complete(coroutine(*args, **kwargs))
        finally:
            self._loop = loop

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)

    def background_manager(
        self, coroutine: typing.Callable, args: typing.Any
    ) -> "BackgroundManager":
        return BackgroundManager(coroutine, args)


class BackgroundManager(BaseBackgroundManager):
    def __init__(self, coroutine: typing.Callable, args: typing.Any) -> None:
        self.coroutine = coroutine
        self.args = args

    async def __aenter__(self) -> "BackgroundManager":
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.coroutine(*self.args))
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.task
        if exc_type is None:
            self.task.result()
