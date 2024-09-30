"""
Async environment-agnostic concurrency utilities that are only used in tests.
"""

import asyncio

from sniffio import current_async_library
import trio


async def sleep(seconds: float) -> None:
    if current_async_library() == "trio":
        await trio.sleep(seconds)  # pragma: no cover
    else:
        await asyncio.sleep(seconds)
