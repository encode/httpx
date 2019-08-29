import functools
import math
import ssl
import typing
from types import TracebackType

import trio

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


def _or_inf(value: typing.Optional[float]) -> float:
    return value if value is not None else float("inf")


class TCPStream(BaseTCPStream):
    def __init__(self, stream: trio.abc.Stream, timeout: TimeoutConfig) -> None:
        self.stream = stream
        self.timeout = timeout
        self.is_eof = False
        self.write_buffer = b""

    def get_http_version(self) -> str:
        if not isinstance(self.stream, trio.SSLStream):
            return "HTTP/1.1"

        ident = self.stream.selected_alpn_protocol()
        if ident is None:
            ident = self.stream.selected_npn_protocol()

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
            read_timeout = _or_inf(timeout.read_timeout if should_raise else 0.01)

            with trio.move_on_after(read_timeout):
                data = await self.stream.receive_some(max_bytes=n)
                if data == b"":  # pragma: no cover
                    self.is_eof = True
                return data

            if should_raise:
                raise ReadTimeout() from None

    def is_connection_dropped(self) -> bool:
        return self.is_eof

    def write_no_block(self, data: bytes) -> None:
        self.write_buffer += data

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        data += self.write_buffer
        self.write_buffer = b""

        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        write_timeout = _or_inf(timeout.write_timeout)

        while True:
            with trio.move_on_after(write_timeout):
                await self.stream.send_all(data)
                break
            # We check our flag at the first possible moment, in order to
            # allow us to suppress write timeouts, if we've since
            # switched over to read-timeout mode.
            should_raise = flag is None or flag.raise_on_write_timeout
            if should_raise:
                raise WriteTimeout() from None

    async def close(self) -> None:
        await self.stream.aclose()


class PoolSemaphore(BasePoolSemaphore):
    def __init__(self, pool_limits: PoolLimits):
        self.pool_limits = pool_limits

    @property
    def semaphore(self) -> typing.Optional[trio.Semaphore]:
        if not hasattr(self, "_semaphore"):
            max_connections = self.pool_limits.hard_limit
            if max_connections is None:
                self._semaphore = None
            else:
                self._semaphore = trio.Semaphore(
                    max_connections, max_value=max_connections
                )
        return self._semaphore

    async def acquire(self) -> None:
        if self.semaphore is None:
            return

        timeout = _or_inf(self.pool_limits.pool_timeout)

        with trio.move_on_after(timeout):
            await self.semaphore.acquire()
            return

        raise PoolTimeout()

    def release(self) -> None:
        if self.semaphore is None:
            return

        self.semaphore.release()


class TrioBackend(ConcurrencyBackend):
    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> TCPStream:
        connect_timeout = _or_inf(timeout.connect_timeout)

        with trio.move_on_after(connect_timeout) as cancel_scope:
            stream: trio.SocketStream = await trio.open_tcp_stream(hostname, port)
            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                await stream.do_handshake()

        if cancel_scope.cancelled_caught:
            raise ConnectTimeout()

        return TCPStream(stream=stream, timeout=timeout)

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        return await trio.to_thread.run_sync(
            functools.partial(func, **kwargs) if kwargs else func, *args
        )

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        return trio.run(
            functools.partial(coroutine, **kwargs) if kwargs else coroutine, *args
        )

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)

    def create_queue(self, max_size: int) -> BaseQueue:
        return Queue(max_size=max_size)

    def create_event(self) -> BaseEvent:
        return typing.cast(BaseEvent, trio.Event())

    def background_manager(
        self, coroutine: typing.Callable, *args: typing.Any
    ) -> "BackgroundManager":
        return BackgroundManager(coroutine, *args)


class Queue(BaseQueue):
    def __init__(self, max_size: int) -> None:
        self.send_channel, self.receive_channel = trio.open_memory_channel(math.inf)

    async def get(self) -> typing.Any:
        return await self.receive_channel.receive()

    async def put(self, value: typing.Any) -> None:
        await self.send_channel.send(value)


class BackgroundManager(BaseBackgroundManager):
    def __init__(self, coroutine: typing.Callable, *args: typing.Any) -> None:
        self.coroutine = coroutine
        self.args = args
        self.nursery_manager = trio.open_nursery()
        self.nursery: typing.Optional[trio.Nursery] = None

    async def __aenter__(self) -> "BackgroundManager":
        self.nursery = await self.nursery_manager.__aenter__()
        self.nursery.start_soon(self.coroutine, *self.args)
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        assert self.nursery is not None
        await self.nursery_manager.__aexit__(exc_type, exc_value, traceback)
