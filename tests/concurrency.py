"""
This module contains concurrency utilities that are only used in tests, thus not
required as part of the ConcurrencyBackend API.
"""

import asyncio
import functools

import trio

from httpx import AsyncioBackend
from httpx.concurrency.trio import TrioBackend


@functools.singledispatch
async def sleep(backend, seconds: int):
    raise NotImplementedError  # pragma: no cover


@sleep.register(AsyncioBackend)
async def _sleep_asyncio(backend, seconds: int):
    await asyncio.sleep(seconds)


@sleep.register(TrioBackend)
async def _sleep_trio(backend, seconds: int):
    await trio.sleep(seconds)


@functools.singledispatch
async def run_concurrently(backend, *async_fns):
    raise NotImplementedError  # pragma: no cover


@run_concurrently.register(AsyncioBackend)
async def _run_concurrently_asyncio(backend, *async_fns):
    await asyncio.gather(*(fn() for fn in async_fns))


@run_concurrently.register(TrioBackend)
async def _run_concurrently_trio(backend, *async_fns):
    async with trio.open_nursery() as nursery:
        for fn in async_fns:
            nursery.start_soon(fn)
