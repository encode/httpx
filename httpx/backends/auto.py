import ssl
import typing

import sniffio

from ..config import Timeout
from .base import (
    BaseLock,
    BaseSemaphore,
    BaseSocketStream,
    ConcurrencyBackend,
    lookup_backend,
)


class AutoBackend(ConcurrencyBackend):
    @property
    def backend(self) -> ConcurrencyBackend:
        if not hasattr(self, "_backend_implementation"):
            backend = sniffio.current_async_library()
            if backend not in ("asyncio", "trio"):  # pragma: nocover
                raise RuntimeError(f"Unsupported concurrency backend {backend!r}")
            self._backend_implementation = lookup_backend(backend)
        return self._backend_implementation

    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> BaseSocketStream:
        return await self.backend.open_tcp_stream(hostname, port, ssl_context, timeout)

    async def open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> BaseSocketStream:
        return await self.backend.open_uds_stream(path, hostname, ssl_context, timeout)

    def time(self) -> float:
        return self.backend.time()

    def create_semaphore(self, max_value: int, exc_class: type) -> BaseSemaphore:
        return self.backend.create_semaphore(max_value, exc_class)

    def create_lock(self) -> BaseLock:
        return self.backend.create_lock()
