import asyncio
import functools
import ssl
import typing
from types import TracebackType

from ..config import PoolLimits, TimeoutConfig
from ..exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from .base import (
    BaseBackgroundManager,
    BaseEvent,
    BasePoolSemaphore,
    BaseQueue,
    BaseTCPStream,
    ConcurrencyBackend,
    TimeoutFlag,
)

SSL_MONKEY_PATCH_APPLIED = False


def ssl_monkey_patch() -> None:
    """
    Monkey-patch for https://bugs.python.org/issue36709

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


class TCPStream(BaseTCPStream):
    def __init__(
        self,
        stream_reader: asyncio.StreamReader,
        stream_writer: asyncio.StreamWriter,
        timeout: TimeoutConfig,
    ):
        self.stream_reader = stream_reader
        self.stream_writer = stream_writer
        self.timeout = timeout

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: TimeoutConfig
    ) -> BaseTCPStream:
        loop = asyncio.get_event_loop()
        if not hasattr(loop, "start_tls"):  # pragma: no cover
            raise NotImplementedError(
                "asyncio.AbstractEventLoop.start_tls() is only available in Python 3.7+"
            )

        stream_reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(stream_reader)
        transport = self.stream_writer.transport

        loop_start_tls = loop.start_tls  # type: ignore
        transport = await asyncio.wait_for(
            loop_start_tls(
                transport=transport,
                protocol=protocol,
                sslcontext=ssl_context,
                server_hostname=hostname,
            ),
            timeout=timeout.connect_timeout,
        )

        stream_reader.set_transport(transport)
        stream_writer = asyncio.StreamWriter(
            transport=transport, protocol=protocol, reader=stream_reader, loop=loop
        )

        return TCPStream(stream_reader, stream_writer, self.timeout)

    def get_http_version(self) -> str:
        ssl_object = self.stream_writer.get_extra_info("ssl_object")

        if ssl_object is None:
            return "HTTP/1.1"

        ident = ssl_object.selected_alpn_protocol()
        return "HTTP/2" if ident == "h2" else "HTTP/1.1"

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
                # FIX(py3.6): yield control back to the event loop to give it a chance
                # to cancel `.read(n)` before we retry.
                # This prevents concurrent `.read()` calls, which asyncio
                # doesn't seem to allow on 3.6.
                # See: https://github.com/encode/httpx/issues/382
                await asyncio.sleep(0)

        return data

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
                # We check our flag at the first possible moment, in order to
                # allow us to suppress write timeouts, if we've since
                # switched over to read-timeout mode.
                should_raise = flag is None or flag.raise_on_write_timeout
                if should_raise:
                    raise WriteTimeout() from None

    def is_connection_dropped(self) -> bool:
        # Counter-intuitively, what we really want to know here is whether the socket is
        # *readable*, i.e. whether it would return immediately with empty bytes if we
        # called `.recv()` on it, indicating that the other end has closed the socket.
        # See: https://github.com/encode/httpx/pull/143#issuecomment-515181778
        #
        # As it turns out, asyncio checks for readability in the background
        # (see: https://github.com/encode/httpx/pull/276#discussion_r322000402),
        # so checking for EOF or readability here would yield the same result.
        #
        # At the cost of rigour, we check for EOF instead of readability because asyncio
        # does not expose any public API to check for readability.
        # (For a solution that uses private asyncio APIs, see:
        # https://github.com/encode/httpx/pull/143#issuecomment-515202982)

        return self.stream_reader.at_eof()

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

    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseTCPStream:
        try:
            stream_reader, stream_writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(hostname, port, ssl=ssl_context),
                timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

        return TCPStream(
            stream_reader=stream_reader, stream_writer=stream_writer, timeout=timeout
        )

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

    def create_queue(self, max_size: int) -> BaseQueue:
        return typing.cast(BaseQueue, asyncio.Queue(maxsize=max_size))

    def create_event(self) -> BaseEvent:
        return typing.cast(BaseEvent, asyncio.Event())

    def background_manager(
        self, coroutine: typing.Callable, *args: typing.Any
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
