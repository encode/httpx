from typing import Callable, List, Optional, Tuple

import httpcore

from .._models import Request


class MockTransport(httpcore.SyncHTTPTransport, httpcore.AsyncHTTPTransport):
    def __init__(self, handler: Callable) -> None:
        self.handler = handler

    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        ext: dict = None,
    ) -> Tuple[int, List[Tuple[bytes, bytes]], httpcore.SyncByteStream, dict]:
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
            response.ext,
        )

    async def arequest(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        ext: dict = None,
    ) -> Tuple[int, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream, dict]:
        request = Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        await request.aread()
        response = self.handler(request)
        return (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.ext,
        )
