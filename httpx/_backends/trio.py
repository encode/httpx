import ssl
import typing

import trio

from .._config import Timeout
from .._exceptions import ConnectTimeout, ReadTimeout, WriteTimeout
from .._utils import as_network_error
from .base import BaseLock, BaseSemaphore, BaseSocketStream, ConcurrencyBackend


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
            with as_network_error(trio.BrokenResourceError):
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
                with as_network_error(trio.BrokenResourceError):
                    return await self.stream.receive_some(max_bytes=n)

        raise ReadTimeout()

    async def write(self, data: bytes, timeout: Timeout) -> None:
        if not data:
            return

        write_timeout = none_as_inf(timeout.write_timeout)

        with trio.move_on_after(write_timeout):
            async with self.write_lock:
                with as_network_error(trio.BrokenResourceError):
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
        async with self.write_lock:
            await self.stream.aclose()


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
            with as_network_error(OSError):
                stream: trio.SocketStream = await trio.open_tcp_stream(hostname, port)

            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                with as_network_error(trio.BrokenResourceError):
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
            with as_network_error(OSError):
                stream: trio.SocketStream = await trio.open_unix_socket(path)

            if ssl_context is not None:
                stream = trio.SSLStream(stream, ssl_context, server_hostname=hostname)
                with as_network_error(trio.BrokenResourceError):
                    await stream.do_handshake()

            return SocketStream(stream=stream)

        raise ConnectTimeout()

    def time(self) -> float:
        return trio.current_time()

    def create_semaphore(self, max_value: int, exc_class: type) -> BaseSemaphore:
        return Semaphore(max_value, exc_class)

    def create_lock(self) -> BaseLock:
        return Lock()


class Semaphore(BaseSemaphore):
    def __init__(self, max_value: int, exc_class: type):
        self.max_value = max_value
        self.exc_class = exc_class

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

        raise self.exc_class()

    def release(self) -> None:
        self.semaphore.release()


class Lock(BaseLock):
    def __init__(self) -> None:
        self._lock = trio.Lock()

    def release(self) -> None:
        self._lock.release()

    async def acquire(self) -> None:
        await self._lock.acquire()
