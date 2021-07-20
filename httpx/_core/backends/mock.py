from typing import List

from ..base import Origin
from .base import AsyncNetworkBackend, AsyncNetworkStream, NetworkBackend, NetworkStream


class MockStream(NetworkStream):
    def __init__(self, buffer: List[bytes]) -> None:
        self._original_buffer = buffer
        self._current_buffer = list(self._original_buffer)

    def read(self, max_bytes: int, timeout: float = None) -> bytes:
        if not self._current_buffer:
            self._current_buffer = list(self._original_buffer)
        return self._current_buffer.pop(0)

    def write(self, buffer: bytes, timeout: float = None) -> None:
        pass

    def close(self) -> None:
        pass


class MockBackend(NetworkBackend):
    def __init__(self, buffer: List[bytes]) -> None:
        self._buffer = buffer

    def connect(self, origin: Origin) -> NetworkStream:
        return MockStream(self._buffer)


class AsyncMockStream(AsyncNetworkStream):
    def __init__(self, buffer: List[bytes]) -> None:
        self._original_buffer = buffer
        self._current_buffer = list(self._original_buffer)

    async def read(self, max_bytes: int, timeout: float = None) -> bytes:
        if not self._current_buffer:
            self._current_buffer = list(self._original_buffer)
        return self._current_buffer.pop(0)

    async def write(self, buffer: bytes, timeout: float = None) -> None:
        pass

    async def aclose(self) -> None:
        pass


class AsyncMockBackend(AsyncNetworkBackend):
    def __init__(self, buffer: List[bytes]) -> None:
        self._buffer = buffer

    async def connect(self, origin: Origin) -> AsyncNetworkStream:
        return AsyncMockStream(self._buffer)
