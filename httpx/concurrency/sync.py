import concurrent.futures
import errno
import functools
import queue
import socket
import ssl
import threading
import time
import typing
from types import TracebackType

from ..config import PoolLimits, TimeoutConfig
from ..exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from .base import (
    BaseBackgroundManager,
    BaseEvent,
    BasePoolSemaphore,
    BaseQueue,
    BaseSocketStream,
    ConcurrencyBackend,
    TimeoutFlag,
)
from .sync_utils.wait import wait_for_socket as default_wait_for_socket


class SocketStream(BaseSocketStream):
    def __init__(
        self,
        sock: socket.socket,
        timeout: TimeoutConfig,
        wait_for_socket: typing.Callable = default_wait_for_socket,
    ):
        self.sock = sock
        self.timeout = timeout
        self.wait_for_socket = wait_for_socket
        self.write_buffer = b""
        # Keep the socket in non-blocking mode, except during connect() and
        # during the SSL handshake.
        self.sock.setblocking(False)

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: TimeoutConfig
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

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> bytes:
        if timeout is None:
            timeout = self.timeout

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

    def write_no_block(self, data: bytes) -> None:
        self.write_buffer += data  # pragma: no cover

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        if self.write_buffer:
            previous_data = self.write_buffer
            # Reset before recursive call, otherwise we'll go through
            # this branch indefinitely.
            self.write_buffer = b""
            try:
                await self.write(previous_data, timeout=timeout, flag=flag)
            except WriteTimeout:
                self.writer_buffer = previous_data
                raise

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

    def is_connection_dropped(self) -> bool:
        # Counter-intuitively, what we really want to know here is whether the socket is
        # *readable*, i.e. whether it would return immediately with empty bytes if we
        # called `.recv()` on it, indicating that the other end has closed the socket.
        # See: https://github.com/encode/httpx/pull/143#issuecomment-515181778
        return self.wait_for_socket(self.sock, read=True, timeout=0)

    async def close(self) -> None:
        self.sock.close()


class PoolSemaphore(BasePoolSemaphore):
    def __init__(self, pool_limits: PoolLimits):
        self.pool_limits = pool_limits

    @property
    def semaphore(self) -> typing.Optional[threading.BoundedSemaphore]:
        if not hasattr(self, "_semaphore"):
            max_connections = self.pool_limits.hard_limit
            if max_connections is None:
                self._semaphore = None
            else:
                self._semaphore = threading.BoundedSemaphore(value=max_connections)
        return self._semaphore

    async def acquire(self) -> None:
        if self.semaphore is None:
            return

        timeout = self.pool_limits.pool_timeout

        if timeout is None:
            self.semaphore.acquire()
            return

        acquired = self.semaphore.acquire(blocking=True, timeout=timeout)
        if not acquired:
            raise PoolTimeout()

    def release(self) -> None:
        if self.semaphore is None:
            return

        self.semaphore.release()


class SyncBackend(ConcurrencyBackend):
    """
    Concurrency backend that performs synchronous I/O operations
    while exposing async-annotated methods.
    """

    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
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

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        # This backend is a blocking one anyway, so no need to use
        # a threadpool here. Just fake it.
        return func(*args, **kwargs)

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        if kwargs:
            coroutine = functools.partial(coroutine, **kwargs)
        return run_secretly_sync_async_function(coroutine, *args)

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)

    def create_queue(self, max_size: int) -> BaseQueue:
        return Queue(max_size=max_size)

    def create_event(self) -> BaseEvent:
        return Event()

    def background_manager(
        self, coroutine: typing.Callable, *args: typing.Any
    ) -> "BackgroundManager":
        return BackgroundManager(coroutine, args)


class Queue(BaseQueue):
    def __init__(self, max_size: int) -> None:
        self.queue: queue.Queue[typing.Any] = queue.Queue(maxsize=max_size)

    async def get(self) -> typing.Any:
        return self.queue.get()

    async def put(self, value: typing.Any) -> None:
        return self.queue.put(value)


class Event(BaseEvent):
    def __init__(self) -> None:
        self.event = threading.Event()

    def set(self) -> None:
        self.event.set()

    def is_set(self) -> bool:
        return self.event.is_set()

    async def wait(self) -> None:
        self.event.wait()

    def clear(self) -> None:
        self.event.clear()


class BackgroundManager(BaseBackgroundManager):
    def __init__(self, coroutine: typing.Callable, args: typing.Any) -> None:
        self.coroutine = coroutine
        self.args = args
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.future: typing.Optional[concurrent.futures.Future[typing.Any]] = None

    async def __aenter__(self) -> "BackgroundManager":
        self.executor.__enter__()
        self.future = self.executor.submit(
            run_secretly_sync_async_function, self.coroutine, *self.args
        )
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        assert self.future is not None
        try:
            # Wait for the coroutine to finish.
            # If the coroutine raises an exception, it will surface here.
            self.future.result()
        finally:
            # Be sure to shutdown the thread pool.
            self.executor.__exit__(exc_type, exc_value, traceback)


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
