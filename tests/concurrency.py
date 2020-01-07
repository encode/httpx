"""
This module contains concurrency utilities that are only used in tests, thus not
required as part of the ConcurrencyBackend API.
"""

import asyncio

import sniffio
import trio


async def sleep(seconds: float):
    if sniffio.current_async_library() == "trio":
        await trio.sleep(seconds)
    else:
        await asyncio.sleep(seconds)


async def run_concurrently(*coroutines):
    if sniffio.current_async_library() == "trio":
        async with trio.open_nursery() as nursery:
            for coroutine in coroutines:
                nursery.start_soon(coroutine)
    else:
        coros = (coroutine() for coroutine in coroutines)
        await asyncio.gather(*coros)


def get_cipher(stream):
    if sniffio.current_async_library() == "trio":
        return (
            stream.stream.cipher()
            if isinstance(stream.stream, trio.SSLStream)
            else None
        )
    else:
        return stream.stream_writer.get_extra_info("cipher", default=None)
