import sys

import pytest
import trio

from httpx import AsyncioBackend, HTTPVersionConfig, SSLConfig, TimeoutConfig
from httpx.concurrency.trio import TrioBackend
from tests.concurrency import run_concurrently


@pytest.mark.parametrize(
    "backend, get_cipher",
    [
        pytest.param(
            AsyncioBackend(),
            lambda stream: stream.stream_writer.get_extra_info("cipher", default=None),
            marks=pytest.mark.asyncio,
        ),
        pytest.param(
            TrioBackend(),
            lambda stream: (
                stream.stream.cipher()
                if isinstance(stream.stream, trio.SSLStream)
                else None
            ),
            marks=pytest.mark.trio,
        ),
    ],
)
async def test_start_tls_on_socket_stream(https_server, backend, get_cipher):
    """
    See that the concurrency backend can make a connection without TLS then
    start TLS on an existing connection.
    """
    if isinstance(backend, AsyncioBackend) and sys.version_info < (3, 7):
        pytest.xfail(reason="Requires Python 3.7+ for AbstractEventLoop.start_tls()")

    ctx = SSLConfig().load_ssl_context_no_verify(HTTPVersionConfig())
    timeout = TimeoutConfig(5)

    stream = await backend.open_tcp_stream(
        https_server.url.host, https_server.url.port, None, timeout
    )

    try:
        assert stream.is_connection_dropped() is False
        assert get_cipher(stream) is None

        stream = await stream.start_tls(https_server.url.host, ctx, timeout)
        assert stream.is_connection_dropped() is False
        assert get_cipher(stream) is not None

        await stream.write(b"GET / HTTP/1.1\r\n\r\n")

        # stream.read() only gives us *up to* as much data as we ask for. In order to
        # cleanly close the stream, we must read until the end of the HTTP response.
        read = b""
        ended = False
        for _ in range(5):  # Try read some (not too large) number of times...
            read += await stream.read(8192, timeout)
            # We know we're at the end of the response when we've received the body plus
            # the terminating CRLFs.
            if b"Hello, world!" in read and read.endswith(b"\r\n\r\n"):
                ended = True
                break

        assert ended
        assert read.startswith(b"HTTP/1.1 200 OK\r\n")

    finally:
        await stream.close()


async def test_concurrent_read(server, backend):
    """
    Regression test for: https://github.com/encode/httpx/issues/527
    """
    stream = await backend.open_tcp_stream(
        server.url.host, server.url.port, ssl_context=None, timeout=TimeoutConfig(5)
    )
    try:
        await stream.write(b"GET / HTTP/1.1\r\n\r\n")
        await run_concurrently(
            backend, lambda: stream.read(10), lambda: stream.read(10)
        )
    finally:
        await stream.close()
