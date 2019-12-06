import functools
import ssl
import typing

import trio

from ..config import PoolLimits, Timeout
from ..exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from .base import (
    BaseEvent,
    BasePoolSemaphore,
    BaseSocketStream,
    ConcurrencyBackend,
    TimeoutFlag,
)


def _or_inf(value: typing.Optional[float]) -> float:
    return value if value is not None else float("inf")


class SocketStream(BaseSocketStream):
    def __init__(
        self, stream: typing.Union[trio.SocketStream, trio.SSLStream], timeout: Timeout,
    ) -> None:
        self.stream = stream
        self.timeout = timeout
        self.read_lock = trio.Lock()
        self.write_lock = trio.Lock()

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: Timeout
    ) -> "SocketStream":
        connect_timeout = _or_inf(timeout.connect_timeout)
        ssl_stream = trio.SSLStream(
            self.stream, ssl_context=ssl_context, server_hostname=hostname
        )

        with trio.move_on_after(connect_timeout) as cancel_scope:
            await ssl_stream.do_handshake()

        if cancel_scope.cancelled_caught:
            raise ConnectTimeout()

        return SocketStream(ssl_stream, self.timeout)

    def get_http_version(self) -> str:
        if not isinstance(self.stream, trio.SSLStream):
            return "HTTP/1.1"

        ident = self.stream.selected_alpn_protocol()
        return "HTTP/2" if ident == "h2" else "HTTP/1.1"

    async def read(
        self, n: int, timeout: Timeout = None, flag: TimeoutFlag = None
    ) -> bytes:
        if timeout is None:
            timeout = self.timeout

        while True:
            # Check our flag at the first possible moment, and use a fine
            # grained retry loop if we're not yet in read-timeout mode.
            should_raise = flag is None or flag.raise_on_read_timeout
            read_timeout = _or_inf(timeout.read_timeout if should_raise else 0.01)

            with trio.move_on_after(read_timeout):
                async with self.read_lock:
                    return await self.stream.receive_some(max_bytes=n)

            if should_raise:
                raise ReadTimeout() from None

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

    async def write(
        self, data: bytes, timeout: Timeout = None, flag: TimeoutFlag = None
    ) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        write_timeout = _or_inf(timeout.write_timeout)

        while True:
            with trio.move_on_after(write_timeout):
                async with self.write_lock:
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

    async def acquire(self, timeout: float = None) -> None:
        if self.semaphore is None:
            return

        timeout = _or_inf(timeout)

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
        timeout: Timeout,
    ) -> SocketStream:
        connect_timeout = _or_inf(timeout.connect_timeout)

        with trio.move_on_after(connect_timeout) as cancel_scope:
            stream: trio.SocketStream = await trio.open_tcp_stream(hostname, port)
            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                await stream.do_handshake()

        if cancel_scope.cancelled_caught:
            raise ConnectTimeout()

        return SocketStream(stream=stream, timeout=timeout)

    async def open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> SocketStream:
        connect_timeout = _or_inf(timeout.connect_timeout)

        with trio.move_on_after(connect_timeout) as cancel_scope:
            stream: trio.SocketStream = await trio.open_unix_socket(path)
            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                await stream.do_handshake()

        if cancel_scope.cancelled_caught:
            raise ConnectTimeout()

        return SocketStream(stream=stream, timeout=timeout)

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

    async def fork(
        self,
        coroutine1: typing.Callable,
        args1: typing.Sequence,
        coroutine2: typing.Callable,
        args2: typing.Sequence,
    ) -> None:
        try:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(coroutine1, *args1)
                nursery.start_soon(coroutine2, *args2)
        except trio.MultiError as exc:
            # In practice, we don't actually care about raising both
            # exceptions, so let's raise either indeterminantly.
            raise exc.exceptions[0]

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)

    def create_event(self) -> BaseEvent:
        return Event()


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
