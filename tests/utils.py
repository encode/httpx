import contextlib
import logging
import os
from typing import Callable, List, Optional, Tuple

import httpcore

import httpx
from httpx import _utils


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

    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        ext: dict = None,
    ) -> Tuple[int, List[Tuple[bytes, bytes]], httpcore.SyncByteStream, dict]:
        request = httpx.Request(
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
        request = httpx.Request(
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
