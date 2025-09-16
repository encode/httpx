import concurrent.futures
import contextlib
import contextvars
import select
import socket
import ssl
import threading
import time
import types
import typing

from ._streams import Stream


__all__ = ["NetworkBackend", "NetworkStream", "timeout"]

_timeout_stack: contextvars.ContextVar[list[float]] = contextvars.ContextVar("timeout_context", default=[])


@contextlib.contextmanager
def timeout(duration: float) -> typing.Iterator[None]:
    """
    A context managed timeout API.

    with timeout(1.0):
        ...
    """
    now = time.monotonic()
    until = now + duration
    stack = typing.cast(list[float], _timeout_stack.get())
    stack = [until] + stack
    token = _timeout_stack.set(stack)
    try:
        yield
    finally:
        _timeout_stack.reset(token)


def get_current_timeout() -> float | None:
    stack = _timeout_stack.get()
    if not stack:
        return None
    soonest = min(stack)
    now = time.monotonic()
    remaining = soonest - now
    if remaining <= 0.0:
        raise TimeoutError()
    return remaining


class NetworkStream(Stream):
    def __init__(self, sock: socket.socket, address: tuple[str, int]) -> None:
        self._socket = sock
        self._address = address
        self._is_tls = False
        self._is_closed = False

    @property
    def host(self) -> str:
        return self._address[0]

    @property
    def port(self) -> int:
        return self._address[1]

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = 64 * 1024
        timeout = get_current_timeout()
        self._socket.settimeout(timeout)
        content = self._socket.recv(size)
        return content

    def write(self, buffer: bytes) -> None:
        while buffer:
            timeout = get_current_timeout()
            self._socket.settimeout(timeout)
            n = self._socket.send(buffer)
            buffer = buffer[n:]

    def close(self) -> None:
        if not self._is_closed:
            self._is_closed = True
            self._socket.close()

    def __repr__(self):
        description = ""
        description += " TLS" if self._is_tls else ""
        description += " CLOSED" if self._is_closed else ""
        return f"<NetworkStream [{self.host}:{self.port}{description}]>"

    def __del__(self):
        if not self._is_closed:
            import warnings
            warnings.warn(f"NetworkStream was garbage collected without being closed.")

    def __enter__(self) -> "NetworkStream":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ):
        self.close()


class NetworkListener:
    def __init__(self, sock: socket.socket, address: tuple[str, int]) -> None:
        self._server_socket = sock
        self._address = address
        self._is_closed = False

    @property
    def host(self):
        return self._address[0]

    @property
    def port(self):
        return self._address[1]

    def accept(self) -> NetworkStream | None:
        """
        Blocks until an incoming connection is accepted, and returns the NetworkStream.
        Stops blocking and returns `None` once the listener is closed.
        """
        while not self._is_closed:
            r, _, _ = select.select([self._server_socket], [], [], 3)
            if r:
                sock, address = self._server_socket.accept()
                return NetworkStream(sock, address)
        return None

    def close(self):
        self._is_closed = True
        self._server_socket.close()

    def __del__(self):
        if not self._is_closed:
            import warnings
            warnings.warn("NetworkListener was garbage collected without being closed.")

    def __enter__(self) -> "NetworkListener":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ):
        self.close()


class NetworkServer:
    def __init__(self, listener: NetworkListener, handler: typing.Callable[[NetworkStream], None]) -> None:
        self.listener = listener
        self.handler = handler
        self._max_workers = 5
        self._executor = None
        self._thread = None
        self._streams = list[NetworkStream]

    @property
    def host(self):
        return self.listener.host

    @property
    def port(self):
        return self.listener.port

    def __enter__(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
        self._executor.submit(self._serve)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.listener.close()
        self._executor.shutdown(wait=True)

    def _serve(self):
        while stream := self.listener.accept():
            self._executor.submit(self._handler, stream)

    def _handler(self, stream):
        try:
            self.handler(stream)
        finally:
            stream.close()


class NetworkBackend:
    def __init__(self, ssl_ctx: ssl.SSLContext | None = None):
        self._ssl_ctx = self.create_default_context() if ssl_ctx is None else ssl_ctx

    def create_default_context(self) -> ssl.SSLContext:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())

    def connect(self, host: str, port: int) -> NetworkStream:
        """
        Connect to the given address, returning a NetworkStream instance.
        """
        address = (host, port)
        timeout = get_current_timeout()
        sock = socket.create_connection(address, timeout=timeout)
        return NetworkStream(sock, address)

    def connect_tls(self, host: str, port: int, hostname: str = '') -> NetworkStream:
        """
        Connect to the given address, returning a NetworkStream instance.
        """
        address = (host, port)
        hostname = hostname or host
        timeout = get_current_timeout()
        sock = socket.create_connection(address, timeout=timeout)
        sock = self._ssl_ctx.wrap_socket(sock, server_hostname=hostname)
        return NetworkStream(sock, address)

    def listen(self, host: str, port: int) -> NetworkListener:
        """
        List on the given address, returning a NetworkListener instance.
        """
        address = (host, port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        sock.listen(5)
        sock.setblocking(False)
        return NetworkListener(sock, address)

    def serve(self, host: str, port: int, handler: typing.Callable[[NetworkStream], None]) -> NetworkServer:
        listener = self.listen(host, port)
        return NetworkServer(listener, handler)

    def __repr__(self):
        return "<NetworkBackend [threaded]>"


Semaphore = threading.Semaphore
Lock = threading.Lock
sleep = time.sleep
