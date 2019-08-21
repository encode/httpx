import sys

import pytest

from httpx import AsyncioBackend, HTTPVersionConfig, SSLConfig, TimeoutConfig


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="Requires Python 3.7+ for AbstractEventLoop.start_tls()",
)
@pytest.mark.asyncio
async def test_https_get_with_ssl_defaults(https_server):
    """
    See that the backend can make a connection without TLS then
    start TLS on an existing connection.
    """
    backend = AsyncioBackend()
    ctx = SSLConfig().load_ssl_context_no_verify(HTTPVersionConfig())
    timeout = TimeoutConfig(5)

    stream = await backend.connect("127.0.0.1", 8001, None, timeout)
    assert stream.is_connection_dropped() is False

    stream = await backend.start_tls(stream, "127.0.0.1", ctx, timeout)
    assert stream.is_connection_dropped() is False

    await stream.write(b"GET / HTTP/1.1\r\n\r\n")
    assert (await stream.read(8192, timeout)).startswith(b"HTTP/1.1 200 OK\r\n")
