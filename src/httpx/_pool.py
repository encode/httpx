import time
import typing
import types

from ._content import Content
from ._headers import Headers
from ._network import Lock, NetworkBackend, Semaphore
from ._parsers import HTTPParser
from ._response import Response
from ._request import Request
from ._streams import HTTPStream, Stream
from ._urls import URL


__all__ = [
    "Transport",
    "ConnectionPool",
    "Connection",
    "open_connection",
]


class Transport:
    def send(self, request: Request) -> Response:
        raise NotImplementedError()

    def close(self):
        pass

    def request(
        self,
        method: str,
        url: URL | str,
        headers: Headers | dict[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Response:
        request = Request(method, url, headers=headers, content=content)
        with self.send(request) as response:
            response.read()
        return response

    def stream(
        self,
        method: str,
        url: URL | str,
        headers: Headers | dict[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Response:
        request = Request(method, url, headers=headers, content=content)
        response = self.send(request)
        return response


class ConnectionPool(Transport):
    def __init__(self, backend: NetworkBackend | None = None):
        if backend is None:
            backend = NetworkBackend()

        self._connections: list[Connection] = []
        self._network_backend = backend
        self._limit_concurrency = Semaphore(100)
        self._closed = False

    # Public API...
    def send(self, request: Request) -> Response:
        if self._closed:
            raise RuntimeError("ConnectionPool is closed.")

        # TODO: concurrency limiting
        self._cleanup()
        connection = self._get_connection(request)
        response = connection.send(request)
        return response

    def close(self):
        self._closed = True
        closing = list(self._connections)
        self._connections = []
        for conn in closing:
            conn.close()

    # Create or reuse connections as required...
    def _get_connection(self, request: Request) -> "Connection":
        # Attempt to reuse an existing connection.
        url = request.url
        origin = URL(scheme=url.scheme, host=url.host, port=url.port)
        now = time.monotonic()
        for conn in self._connections:
            if conn.origin() == origin and conn.is_idle() and not conn.is_expired(now):
                return conn

        # Or else create a new connection.
        conn = open_connection(
            origin,
            hostname=request.headers["Host"],
            backend=self._network_backend
        )
        self._connections.append(conn)
        return conn

    # Connection pool management...
    def _cleanup(self) -> None:
        now = time.monotonic()
        for conn in list(self._connections):
            if conn.is_expired(now):
                conn.close()
            if conn.is_closed():
                self._connections.remove(conn)

    @property
    def connections(self) -> typing.List['Connection']:
        return [c for c in self._connections]

    def description(self) -> str:
        counts = {"active": 0}
        for status in [c.description() for c in self._connections]:
            counts[status] = counts.get(status, 0) + 1
        return ", ".join(f"{count} {status}" for status, count in counts.items())

    # Builtins...
    def __repr__(self) -> str:
        return f"<ConnectionPool [{self.description()}]>"

    def __del__(self):
        if not self._closed:
            import warnings
            warnings.warn("ConnectionPool was garbage collected without being closed.")

    def __enter__(self) -> "ConnectionPool":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self.close()


class Connection(Transport):
    def __init__(self, stream: Stream, origin: URL | str):
        self._stream = stream
        self._origin = URL(origin)
        self._keepalive_duration = 5.0
        self._idle_expiry = time.monotonic() + self._keepalive_duration
        self._request_lock = Lock()
        self._parser = HTTPParser(stream, mode='CLIENT')

    # API for connection pool management...
    def origin(self) -> URL:
        return self._origin

    def is_idle(self) -> bool:
        return self._parser.is_idle()

    def is_expired(self, when: float) -> bool:
        return self._parser.is_idle() and when > self._idle_expiry

    def is_closed(self) -> bool:
        return self._parser.is_closed()

    def description(self) -> str:
        return self._parser.description()

    # API entry points...
    def send(self, request: Request) -> Response:
        #async with self._request_lock:
        #    try:
        self._send_head(request)
        self._send_body(request)
        code, headers = self._recv_head()
        stream = HTTPStream(self._recv_body, self._complete)
        # TODO...
        return Response(code, headers=headers, content=stream)
        #    finally:
        #        await self._cycle_complete()

    def close(self) -> None:
        with self._request_lock:
            self._close()

    # Top-level API for working directly with a connection.
    def request(
        self,
        method: str,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Response:
        url = self._origin.join(url)
        request = Request(method, url, headers=headers, content=content)
        with self.send(request) as response:
            response.read()
        return response

    def stream(
        self,
        method: str,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Response:
        url = self._origin.join(url)
        request = Request(method, url, headers=headers, content=content)
        return self.send(request)

    # Send the request...
    def _send_head(self, request: Request) -> None:
        method = request.method.encode('ascii')
        target = request.url.target.encode('ascii')
        protocol = b'HTTP/1.1'
        self._parser.send_method_line(method, target, protocol)
        headers = [
            (k.encode('ascii'), v.encode('ascii'))
            for k, v in request.headers.items()
        ]
        self._parser.send_headers(headers)

    def _send_body(self, request: Request) -> None:
        while data := request.stream.read(64 * 1024):
            self._parser.send_body(data)
        self._parser.send_body(b'')

    # Receive the response...
    def _recv_head(self) -> tuple[int, Headers]:
        _, code, _ = self._parser.recv_status_line()
        h = self._parser.recv_headers()
        headers = Headers([
            (k.decode('ascii'), v.decode('ascii'))
            for k, v in h
        ])
        return code, headers

    def _recv_body(self) -> bytes:
        return self._parser.recv_body()

    # Request/response cycle complete...
    def _complete(self) -> None:
        self._parser.complete()
        self._idle_expiry = time.monotonic() + self._keepalive_duration

    def _close(self) -> None:
        self._parser.close()

    # Builtins...
    def __repr__(self) -> str:
        return f"<Connection [{self._origin} {self.description()}]>"

    def __enter__(self) -> "Connection":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ):
        self.close()


def open_connection(
        url: URL | str,
        hostname: str = '',
        backend: NetworkBackend | None = None,
    ) -> Connection:

    if isinstance(url, str):
        url = URL(url)

    if url.scheme not in ("http", "https"):
        raise ValueError("URL scheme must be 'http://' or 'https://'.")
    if backend is None:
        backend = NetworkBackend()

    host = url.host
    port = url.port or {"http": 80, "https": 443}[url.scheme]

    if url.scheme == "https":
        stream = backend.connect_tls(host, port, hostname)
    else:
        stream = backend.connect(host, port)

    return Connection(stream, url)
