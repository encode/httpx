import asyncio
from typing import Callable, List, Optional, Tuple

from .._models import Request
from .base import AsyncBaseTransport, AsyncByteStream, BaseTransport, SyncByteStream


class MockTransport(AsyncBaseTransport, BaseTransport):
    def __init__(self, handler: Callable) -> None:
        self.handler = handler

    def handle_request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]],
        stream: SyncByteStream,
        extensions: dict,
    ) -> Tuple[int, List[Tuple[bytes, bytes]], SyncByteStream, dict]:
        request = Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        request.read()
        response = self.handler(request)
        return (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.extensions,
        )

    async def handle_async_request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]],
        stream: AsyncByteStream,
        extensions: dict,
    ) -> Tuple[int, List[Tuple[bytes, bytes]], AsyncByteStream, dict]:
        request = Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        await request.aread()

        response = self.handler(request)

        # Allow handler to *optionally* be an `async` function.
        # If it is, then the `response` variable need to be awaited to actually
        # return the result.

        # https://simonwillison.net/2020/Sep/2/await-me-maybe/
        if asyncio.iscoroutine(response):
            response = await response

        return (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.extensions,
        )
