import contextlib
import logging
import os
from typing import Callable, List, Mapping, Optional, Tuple

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


class MockTransport(httpcore.SyncHTTPTransport):
    def __init__(self, handler: Callable) -> None:
        self.handler = handler

    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        timeout: Mapping[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.SyncByteStream]:
        raw_scheme, raw_host, port, raw_path = url
        scheme = raw_scheme.decode("ascii")
        host = raw_host.decode("ascii")
        port_str = "" if port is None else f":{port}"
        path = raw_path.decode("ascii")

        request_headers = httpx.Headers(headers)
        data = (
            (item for item in stream)
            if stream
            and (
                "Content-Length" in request_headers
                or "Transfer-Encoding" in request_headers
            )
            else None
        )

        request = httpx.Request(
            method=method.decode("ascii"),
            url=f"{scheme}://{host}{port_str}{path}",
            headers=request_headers,
            data=data,
        )
        request.read()
        response = self.handler(request)
        return (
            response.http_version.encode("ascii")
            if response.http_version
            else b"HTTP/1.1",
            response.status_code,
            response.reason_phrase.encode("ascii"),
            response.headers.raw,
            response._raw_stream,
        )
