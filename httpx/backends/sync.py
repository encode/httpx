import errno
import functools
import socket
import ssl
import threading
import time
import typing

from .._sync.backends.base import (
    SyncBaseLock,
    SyncBaseSemaphore,
    SyncBaseSocketStream,
    SyncConcurrencyBackend,
)
from ..config import Timeout
from ..exceptions import ConnectTimeout, ReadTimeout, WriteTimeout
from .sync_utils.wait import wait_for_socket as default_wait_for_socket


class SocketStream(SyncBaseSocketStream):
    def __init__(
        self,
        sock: socket.socket,
        timeout: Timeout,
        wait_for_socket: typing.Callable = default_wait_for_socket,
    ):
        self.sock = sock
        self.timeout = timeout
        self.wait_for_socket = wait_for_socket
        self.write_buffer = b""
        # Keep the socket in non-blocking mode, except during connect() and
        # during the SSL handshake.
        self.sock.setblocking(False)

    def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: Timeout
    ) -> "SocketStream":
        self.sock.setblocking(True)
        wrapped = ssl_context.wrap_socket(self.sock, server_hostname=hostname)
        wrapped.setblocking(False)
        return SocketStream(wrapped, timeout=self.timeout)

    def get_http_version(self) -> str:
        if not isinstance(self.sock, ssl.SSLSocket):
            return "HTTP/1.1"
        ident = self.sock.selected_alpn_protocol()
        return "HTTP/2" if ident == "h2" else "HTTP/1.1"

    def _wait(
        self, readable: bool, writable: bool, mode: str, timeout: typing.Optional[float]
    ) -> None:
        assert mode in ("read", "write")
        assert readable or writable
        if not self.wait_for_socket(
            self.sock, read=readable, write=writable, timeout=timeout
        ):
            raise (ReadTimeout() if mode == "read" else WriteTimeout())

    def read(self, n: int, timeout: Timeout) -> bytes:
        read_timeout = timeout.read_timeout
        start = time.time()
        while True:
            try:
                return self.sock.recv(n)
            except ssl.SSLWantReadError:
                self._wait(
                    readable=True, writable=False, mode="read", timeout=read_timeout
                )
            except ssl.SSLWantWriteError:
                self._wait(
                    readable=False, writable=True, mode="read", timeout=read_timeout
                )
            except (OSError, socket.error) as exc:
                if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    self._wait(
                        readable=True, writable=False, mode="read", timeout=read_timeout
                    )
                else:
                    raise

            if read_timeout is not None:
                read_timeout -= time.time() - start
                if read_timeout < 0:
                    raise ReadTimeout()

    def write(self, data: bytes, timeout: Timeout = None,) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout
        write_timeout = timeout.write_timeout
        start = time.time()

        while data:
            made_progress = False
            want_read = False
            want_write = False

            try:
                sent = self.sock.send(data)
                data = data[sent:]
            except ssl.SSLWantReadError:
                want_read = True
            except ssl.SSLWantWriteError:
                want_write = True
            except (OSError, socket.error) as exc:
                if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    want_write = True
                else:
                    raise
            else:
                made_progress = True

            if not made_progress:
                self._wait(
                    readable=want_read,
                    writable=want_write,
                    mode="write",
                    timeout=write_timeout,
                )

            if write_timeout is not None:
                write_timeout -= time.time() - start
                if write_timeout < 0:
                    raise WriteTimeout()

    def is_connection_dropped(self) -> bool:
        # Counter-intuitively, what we really want to know here is whether the socket is
        # *readable*, i.e. whether it would return immediately with empty bytes if we
        # called `.recv()` on it, indicating that the other end has closed the socket.
        # See: https://github.com/encode/httpx/pull/143#issuecomment-515181778
        return self.wait_for_socket(self.sock, read=True, timeout=0)

    def close(self) -> None:
        self.sock.close()


class Semaphore(SyncBaseSemaphore):
    def __init__(self, max_value: int, exc_class: type) -> None:
        self.max_value = max_value
        self.exc_class = exc_class

    @property
    def semaphore(self) -> threading.BoundedSemaphore:
        if not hasattr(self, "_semaphore"):
            self._semaphore = threading.BoundedSemaphore(value=self.max_value)
        return self._semaphore

    def acquire(self, timeout: float = None) -> None:
        if timeout is None:
            self.semaphore.acquire()
            return

        acquired = self.semaphore.acquire(blocking=True, timeout=timeout)

        if not acquired:
            raise self.exc_class()

    def release(self) -> None:
        self.semaphore.release()


class SyncBackend(SyncConcurrencyBackend):
    """
    Concurrency backend that performs synchronous I/O operations
    while exposing async-annotated methods.
    """

    def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> SocketStream:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout.connect_timeout)
            sock.connect((hostname, port))
            if ssl_context is not None:
                sock = ssl_context.wrap_socket(sock, server_hostname=hostname)
        except socket.timeout:
            raise ConnectTimeout()
        except socket.error:
            raise  # TODO: raise an HTTPX-specific exception
        else:
            return SocketStream(sock=sock, timeout=timeout)

    def open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> SocketStream:
        raise NotImplementedError

    def time(self) -> float:
        return time.time()

    def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        # This backend is a blocking one anyway, so no need to use
        # a threadpool here.
        return func(*args, **kwargs)

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        if kwargs:
            coroutine = functools.partial(coroutine, **kwargs)
        return run_secretly_sync_async_function(coroutine, *args)

    def create_semaphore(self, max_value: int, exc_class: type) -> SyncBaseSemaphore:
        return Semaphore(max_value, exc_class)

    def create_lock(self) -> SyncBaseLock:
        return Lock()


class Lock(SyncBaseLock):
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def release(self) -> None:
        self._lock.release()

    def acquire(self) -> None:
        self._lock.acquire()


def run_secretly_sync_async_function(
    async_function: typing.Callable, *args: typing.Any
) -> typing.Any:
    coro = async_function(*args)
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    else:
        raise RuntimeError("This async function is not secretly synchronous.")
