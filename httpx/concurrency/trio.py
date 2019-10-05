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
)


def _or_inf(value: typing.Optional[float]) -> float:
    return value if value is not None else float("inf")


class TCPStream(BaseTCPStream):
    def __init__(
        self,
        stream: typing.Union[trio.SocketStream, trio.SSLStream],
        timeout: TimeoutConfig,
    ) -> None:
        super().__init__(timeout)
        self.stream = stream
        self.write_lock = trio.Lock()

    def get_http_version(self) -> str:
        if not isinstance(self.stream, trio.SSLStream):
            return "HTTP/1.1"

        ident = self.stream.selected_alpn_protocol()
        return "HTTP/2" if ident == "h2" else "HTTP/1.1"

    async def read_or_timeout(self, n: int, timeout: typing.Optional[float]) -> bytes:
        with trio.move_on_after(_or_inf(timeout)):
            return await self.stream.receive_some(max_bytes=n)
        raise ReadTimeout()

    async def write_or_timeout(
        self, data: bytes, timeout: typing.Optional[float]
    ) -> None:
        with trio.move_on_after(_or_inf(timeout)):
            async with self.write_lock:
                await self.stream.send_all(data)
            return
        raise WriteTimeout()

    def is_connection_dropped(self) -> bool:
        # Adapted from: https://github.com/encode/httpx/pull/143#issuecomment-515202982
        stream = self.stream

        # Peek through any SSLStream wrappers to get the underlying SocketStream.
        while hasattr(stream, "transport_stream"):
            stream = stream.transport_stream
        assert isinstance(stream, trio.SocketStream)

        # Counter-intuitively, what we really want to know here is whether the socket is
        # *readable*, i.e. whether it would return immediately with empty bytes if we
        # called `.recv()` on it, indicating that the other end has closed the socket.
        # See: https://github.com/encode/httpx/pull/143#issuecomment-515181778
        return stream.socket.is_readable()

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
        return Event()

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


class Event(BaseEvent):
    def __init__(self) -> None:
        self._event = trio.Event()

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    async def wait(self) -> None:
        await self._event.wait()

    def clear(self) -> None:
        # trio.Event.clear() was deprecated in Trio 0.12.
        # https://github.com/python-trio/trio/issues/637
        self._event = trio.Event()


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
