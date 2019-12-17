import functools
import ssl
import typing

import trio

from ..config import Timeout
from ..exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from .base import BaseEvent, BasePoolSemaphore, BaseSocketStream, ConcurrencyBackend


def none_as_inf(value: typing.Optional[float]) -> float:
    return value if value is not None else float("inf")


class SocketStream(BaseSocketStream):
    def __init__(
        self, stream: typing.Union[trio.SocketStream, trio.SSLStream],
    ) -> None:
        self.stream = stream
        self.read_lock = trio.Lock()
        self.write_lock = trio.Lock()

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: Timeout
    ) -> "SocketStream":
        connect_timeout = none_as_inf(timeout.connect_timeout)
        ssl_stream = trio.SSLStream(
            self.stream, ssl_context=ssl_context, server_hostname=hostname
        )

        with trio.move_on_after(connect_timeout):
            await ssl_stream.do_handshake()
            return SocketStream(ssl_stream)

        raise ConnectTimeout()

    def get_http_version(self) -> str:
        if not isinstance(self.stream, trio.SSLStream):
            return "HTTP/1.1"

        ident = self.stream.selected_alpn_protocol()
        return "HTTP/2" if ident == "h2" else "HTTP/1.1"

    async def read(self, n: int, timeout: Timeout) -> bytes:
        read_timeout = none_as_inf(timeout.read_timeout)

        with trio.move_on_after(read_timeout):
            async with self.read_lock:
                return await self.stream.receive_some(max_bytes=n)

        raise ReadTimeout()

    async def write(self, data: bytes, timeout: Timeout) -> None:
        if not data:
            return

        write_timeout = none_as_inf(timeout.write_timeout)

        with trio.move_on_after(write_timeout):
            async with self.write_lock:
                return await self.stream.send_all(data)

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
    def __init__(self, max_value: int):
        self.max_value = max_value

    @property
    def semaphore(self) -> trio.Semaphore:
        if not hasattr(self, "_semaphore"):
            self._semaphore = trio.Semaphore(self.max_value, max_value=self.max_value)
        return self._semaphore

    async def acquire(self, timeout: float = None) -> None:
        timeout = none_as_inf(timeout)

        with trio.move_on_after(timeout):
            await self.semaphore.acquire()
            return

        raise PoolTimeout()

    def release(self) -> None:
        self.semaphore.release()


class TrioBackend(ConcurrencyBackend):
    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> SocketStream:
        connect_timeout = none_as_inf(timeout.connect_timeout)

        with trio.move_on_after(connect_timeout):
            stream: trio.SocketStream = await trio.open_tcp_stream(hostname, port)
            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                await stream.do_handshake()
            return SocketStream(stream=stream)

        raise ConnectTimeout()

    async def open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> SocketStream:
        connect_timeout = none_as_inf(timeout.connect_timeout)

        with trio.move_on_after(connect_timeout):
            stream: trio.SocketStream = await trio.open_unix_socket(path)
            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                await stream.do_handshake()
            return SocketStream(stream=stream)

        raise ConnectTimeout()

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

    def time(self) -> float:
        return trio.current_time()

    def get_semaphore(self, max_value: int) -> BasePoolSemaphore:
        return PoolSemaphore(max_value)

    def create_event(self) -> BaseEvent:
        return Event()


class Event(BaseEvent):
    def __init__(self) -> None:
        self._event = trio.Event()

    def set(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()
