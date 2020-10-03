import contextlib
import logging
import os
from typing import Callable, Iterator, AsyncIterator, List, Optional, Tuple

import httpcore

import httpx
from httpx import _utils
from httpx._compat import asynccontextmanager


@contextlib.contextmanager
def override_log_level(log_level: str):
    os.environ["HTTPX_LOG_LEVEL"] = log_level

    # Force a reload on the logging handlers
    _utils._LOGGER_INITIALIZED = False
    _utils.get_logger("httpx")

    try:
        yield
    finally:
        # Reset the logger so we don't have verbose output in all unit tests
        logging.getLogger("httpx").handlers = []


class MockTransport(httpcore.SyncHTTPTransport, httpcore.AsyncHTTPTransport):
    def __init__(self, handler: Callable) -> None:
        self.handler = handler

    @contextlib.contextmanager
    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        ext: dict = None,
    ) -> Iterator[Tuple[int, List[Tuple[bytes, bytes]], httpcore.SyncByteStream, dict]]:
        request = httpx.Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        request.read()
        response = self.handler(request)
        yield (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.ext,
        )

    @asynccontextmanager
    async def arequest(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        ext: dict = None,
    ) -> AsyncIterator[
        Tuple[int, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream, dict]
    ]:
        request = httpx.Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        await request.aread()
        response = self.handler(request)
        yield (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.ext,
        )
