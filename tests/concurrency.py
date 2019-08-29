"""
This module contains concurrency utilities that are only used in tests, thus not
required as part of the ConcurrencyBackend API.
"""

import asyncio
import functools

from httpx import AsyncioBackend


@functools.singledispatch
async def sleep(backend, seconds: int):
    raise NotImplementedError  # pragma: no cover


@sleep.register(AsyncioBackend)
async def _sleep_asyncio(backend, seconds: int):
    await asyncio.sleep(seconds)


try:
    import trio
    from httpx.concurrency.trio import TrioBackend
except ImportError:  # pragma: no cover
    pass
else:

    @sleep.register(TrioBackend)
    async def _sleep_trio(backend, seconds: int):
        await trio.sleep(seconds)
