"""
This module contains concurrency utilities that are only used in tests, thus not
required as part of the ConcurrencyBackend API.
"""

import asyncio
import functools
import typing

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
async def run_concurrently(backend, *coroutines: typing.Callable[[], typing.Awaitable]):
    raise NotImplementedError  # pragma: no cover


@run_concurrently.register(AsyncioBackend)
async def _run_concurrently_asyncio(backend, *coroutines):
    coros = (coroutine() for coroutine in coroutines)
    await asyncio.gather(*coros)


@run_concurrently.register(TrioBackend)
async def _run_concurrently_trio(backend, *coroutines):
    async with trio.open_nursery() as nursery:
        for coroutine in coroutines:
            nursery.start_soon(coroutine)
