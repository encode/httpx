import pytest
import trio

from httpx import AsyncioBackend, SSLConfig, TimeoutConfig
from httpx.concurrency.trio import TrioBackend
from tests.concurrency import run_concurrently


def get_asyncio_cipher(stream):
    return stream.stream_writer.get_extra_info("cipher", default=None)


def get_trio_cipher(stream):
    return stream.stream.cipher() if isinstance(stream.stream, trio.SSLStream) else None


async def read_response(stream, timeout: float, should_contain: bytes) -> bytes:
    # stream.read() only gives us *up to* as much data as we ask for. In order to
    # cleanly close the stream, we must read until the end of the HTTP response.
    response = b""
    ended = False

    for _ in range(5):  # Try read some (not too large) number of times...
        response += await stream.read(8192, timeout)
        # We know we're at the end of the response when we've received the body plus
        # the terminating CRLFs.
        if should_contain in response and response.endswith(b"\r\n\r\n"):
            ended = True
            break

    assert ended
    return response


@pytest.mark.parametrize(
    "backend, get_cipher",
    [
        pytest.param(AsyncioBackend(), get_asyncio_cipher, marks=pytest.mark.asyncio),
        pytest.param(TrioBackend(), get_trio_cipher, marks=pytest.mark.trio),
    ],
)
async def test_start_tls_on_tcp_socket_stream(https_server, backend, get_cipher):
    ctx = SSLConfig().load_ssl_context_no_verify()
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

        response = await read_response(stream, timeout, should_contain=b"Hello, world")
        assert response.startswith(b"HTTP/1.1 200 OK\r\n")

    finally:
        await stream.close()


@pytest.mark.parametrize(
    "backend, get_cipher",
    [
        pytest.param(AsyncioBackend(), get_asyncio_cipher, marks=pytest.mark.asyncio),
        pytest.param(TrioBackend(), get_trio_cipher, marks=pytest.mark.trio),
    ],
)
async def test_start_tls_on_uds_socket_stream(https_uds_server, backend, get_cipher):
    ctx = SSLConfig().load_ssl_context_no_verify()
    timeout = TimeoutConfig(5)

    stream = await backend.open_uds_stream(
        https_uds_server.config.uds, https_uds_server.url.host, None, timeout
    )

    try:
        assert stream.is_connection_dropped() is False
        assert get_cipher(stream) is None

        stream = await stream.start_tls(https_uds_server.url.host, ctx, timeout)
        assert stream.is_connection_dropped() is False
        assert get_cipher(stream) is not None

        await stream.write(b"GET / HTTP/1.1\r\n\r\n")

        response = await read_response(stream, timeout, should_contain=b"Hello, world")
        assert response.startswith(b"HTTP/1.1 200 OK\r\n")

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
