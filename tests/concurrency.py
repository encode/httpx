"""
Async environment-agnostic concurrency utilities that are only used in tests.
"""

import asyncio

import sniffio
import trio


async def sleep(seconds: float) -> None:
    if sniffio.current_async_library() == "trio":
        await trio.sleep(seconds)  # pragma: no cover
    else:
        await asyncio.sleep(seconds)
