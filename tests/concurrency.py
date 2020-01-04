"""
This module contains concurrency utilities that are only used in tests, thus not
required as part of the ConcurrencyBackend API.
"""

import asyncio
import functools
import typing

import trio

from httpx.backends.asyncio import AsyncioBackend
from httpx.backends.auto import AutoBackend
from httpx.backends.trio import TrioBackend


@functools.singledispatch
async def run_concurrently(backend, *coroutines: typing.Callable[[], typing.Awaitable]):
    raise NotImplementedError  # pragma: no cover


@run_concurrently.register(AutoBackend)
async def _run_concurrently_auto(backend, *coroutines):
    await run_concurrently(backend.backend, *coroutines)


@run_concurrently.register(AsyncioBackend)
async def _run_concurrently_asyncio(backend, *coroutines):
    coros = (coroutine() for coroutine in coroutines)
    await asyncio.gather(*coros)


@run_concurrently.register(TrioBackend)
async def _run_concurrently_trio(backend, *coroutines):
    async with trio.open_nursery() as nursery:
        for coroutine in coroutines:
            nursery.start_soon(coroutine)


@functools.singledispatch
def get_cipher(backend, stream):
    raise NotImplementedError  # pragma: no cover


@get_cipher.register(AutoBackend)
def _get_cipher_auto(backend, stream):
    return get_cipher(backend.backend, stream)


@get_cipher.register(AsyncioBackend)
def _get_cipher_asyncio(backend, stream):
    return stream.stream_writer.get_extra_info("cipher", default=None)


@get_cipher.register(TrioBackend)
def get_trio_cipher(backend, stream):
    return stream.stream.cipher() if isinstance(stream.stream, trio.SSLStream) else None
