"""
This module contains concurrency utilities that are only used in tests, thus not
required as part of the ConcurrencyBackend API.
"""

import asyncio
import functools

import trio

from httpx.backends.asyncio import AsyncioBackend
from httpx.backends.auto import AutoBackend
from httpx.backends.trio import TrioBackend


@functools.singledispatch
async def sleep(backend, seconds: int):
    raise NotImplementedError  # pragma: no cover


@sleep.register(AutoBackend)
async def _sleep_auto(backend, seconds: int):
    return await sleep(backend.backend, seconds=seconds)


@sleep.register(AsyncioBackend)
async def _sleep_asyncio(backend, seconds: int):
    await asyncio.sleep(seconds)


@sleep.register(TrioBackend)
async def _sleep_trio(backend, seconds: int):
    await trio.sleep(seconds)


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
