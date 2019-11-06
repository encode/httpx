import pytest
import trio

from httpx import AsyncioBackend, HTTPVersionConfig, SSLConfig, TimeoutConfig
from httpx.concurrency.trio import TrioBackend


def get_asyncio_cipher(stream):
    return stream.stream_writer.get_extra_info("cipher", default=None)


def get_trio_cipher(stream):
    return stream.stream.cipher() if isinstance(stream.stream, trio.SSLStream) else None


@pytest.mark.parametrize(
    "backend, test_uds, get_cipher",
    [
        pytest.param(
            AsyncioBackend(), False, get_asyncio_cipher, marks=pytest.mark.asyncio
        ),
        pytest.param(
            AsyncioBackend(), True, get_asyncio_cipher, marks=pytest.mark.asyncio
        ),
        pytest.param(TrioBackend(), False, get_trio_cipher, marks=pytest.mark.trio),
        pytest.param(TrioBackend(), True, get_trio_cipher, marks=pytest.mark.trio),
    ],
)
async def test_start_tls_on_socket_stream(
    https_server, https_uds_server, backend, test_uds, get_cipher
):
    """
    See that the concurrency backend can make a connection without TLS then
    start TLS on an existing connection.
    """
    ctx = SSLConfig().load_ssl_context_no_verify(HTTPVersionConfig())
    timeout = TimeoutConfig(5)

    if test_uds:
        assert https_uds_server.config.uds is not None
        stream = await backend.open_uds_stream(
            https_uds_server.config.uds, https_uds_server.url.host, None, timeout
        )
    else:
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
