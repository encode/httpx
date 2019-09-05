import sys

import pytest

from httpx import AsyncioBackend, HTTPVersionConfig, SSLConfig, TimeoutConfig


@pytest.mark.asyncio
async def test_start_tls_on_socket_stream(https_server):
    """
    See that the backend can make a connection without TLS then
    start TLS on an existing connection.
    """
    backend = AsyncioBackend()
    ctx = SSLConfig().load_ssl_context_no_verify(HTTPVersionConfig())
    timeout = TimeoutConfig(5)

    stream = await backend.connect(
        https_server.url.host, https_server.url.port, None, timeout
    )

    try:
        assert stream.is_connection_dropped() is False
        assert stream.stream_writer.get_extra_info("cipher", default=None) is None
        if sys.version_info < (3, 7):
            with pytest.raises(NotImplementedError):
                await backend.start_tls(stream, https_server.url.host, ctx, timeout)
        else:
            stream = await backend.start_tls(
                stream, https_server.url.host, ctx, timeout
            )
            assert stream.is_connection_dropped() is False
            assert (
                stream.stream_writer.get_extra_info("cipher", default=None) is not None
            )

            await stream.write(b"GET / HTTP/1.1\r\n\r\n")
            assert (await stream.read(8192, timeout)).startswith(b"HTTP/1.1 200 OK\r\n")

    finally:
        await stream.close()
