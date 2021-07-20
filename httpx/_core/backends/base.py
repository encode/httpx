import ssl

from ..base import Origin


class NetworkStream:
    def read(self, max_bytes: int, timeout: float = None) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def write(self, buffer: bytes, timeout: float = None) -> None:
        raise NotImplementedError()  # pragma: nocover

    def close(self) -> None:
        raise NotImplementedError()  # pragma: nocover

    def start_tls(
        self, ssl_context: ssl.SSLContext, server_hostname: bytes = None
    ) -> "NetworkStream":
        raise NotImplementedError()  # pragma: nocover


class NetworkBackend:
    def connect(self, origin: Origin) -> NetworkStream:
        raise NotImplementedError()  # pragma: nocover


class AsyncNetworkStream:
    async def read(self, max_bytes: int, timeout: float = None) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    async def write(self, buffer: bytes, timeout: float = None) -> None:
        raise NotImplementedError()  # pragma: nocover

    async def aclose(self) -> None:
        raise NotImplementedError()  # pragma: nocover

    async def start_tls(
        self, ssl_context: ssl.SSLContext, server_hostname: bytes = None
    ) -> "AsyncNetworkStream":
        raise NotImplementedError()  # pragma: nocover


class AsyncNetworkBackend:
    async def connect(self, origin: Origin) -> AsyncNetworkStream:
        raise NotImplementedError()  # pragma: nocover
