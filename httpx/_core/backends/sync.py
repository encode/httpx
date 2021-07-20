import socket
import ssl

from ..base import Origin
from .base import NetworkBackend, NetworkStream


class SyncStream(NetworkStream):
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock

    def read(self, max_bytes: int, timeout: float = None) -> bytes:
        return self._sock.recv(max_bytes)

    def write(self, buffer: bytes, timeout: float = None) -> None:
        while buffer:
            n = self._sock.send(buffer)
            buffer = buffer[n:]

    def close(self) -> None:
        self._sock.close()

    def start_tls(
        self, ssl_context: ssl.SSLContext, server_hostname: bytes = None
    ) -> NetworkStream:
        hostname = None if server_hostname is None else server_hostname.decode("ascii")
        sock = ssl_context.wrap_socket(self._sock, server_hostname=hostname)
        return SyncStream(sock)


class SyncBackend(NetworkBackend):
    def __init__(self, ssl_context: ssl.SSLContext = None) -> None:
        self._ssl_context = (
            ssl.create_default_context() if ssl_context is None else ssl_context
        )

    def connect(self, origin: Origin) -> NetworkStream:
        address = (origin.host.decode("ascii"), origin.port)
        sock = socket.create_connection(address)
        stream: NetworkStream = SyncStream(sock)
        if origin.scheme == b"https":
            stream = stream.start_tls(self._ssl_context, server_hostname=origin.host)
        return stream
