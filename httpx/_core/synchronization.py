import threading
from types import TracebackType
from typing import Type

import trio


class AsyncLock:
    def __init__(self) -> None:
        self._lock = trio.Lock()

    async def __aenter__(self) -> "AsyncLock":
        await self._lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self._lock.release()


class AsyncSemaphore:
    def __init__(self, bound: int) -> None:
        self._semaphore = trio.Semaphore(initial_value=bound, max_value=bound)

    async def acquire_noblock(self) -> bool:
        try:
            self._semaphore.acquire_nowait()
        except trio.WouldBlock:
            return False
        return True

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    async def release(self) -> None:
        self._semaphore.release()


class Lock:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def __enter__(self) -> "Lock":
        self._lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self._lock.release()


class Semaphore:
    def __init__(self, bound: int) -> None:
        self._semaphore = threading.Semaphore(value=bound)

    def acquire_noblock(self) -> bool:
        return self._semaphore.acquire(blocking=False)

    def acquire(self) -> None:
        self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()
