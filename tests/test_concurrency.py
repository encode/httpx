import asyncio

import pytest
import trio

from httpx import Timeout
from httpx.backends.asyncio import AsyncioBackend
from httpx.backends.base import lookup_backend
from httpx.backends.trio import TrioBackend
from httpx.config import SSLConfig
from tests.concurrency import get_cipher, run_concurrently


async def read_response(stream, timeout: Timeout, should_contain: bytes) -> bytes:
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


@pytest.mark.usefixtures("async_environment")
async def test_start_tls_on_tcp_socket_stream(https_server):
    backend = lookup_backend()
    ctx = SSLConfig().load_ssl_context_no_verify()
    timeout = Timeout(5)

    stream = await backend.open_tcp_stream(
        https_server.url.host, https_server.url.port, None, timeout
    )

    try:
        assert stream.is_connection_dropped() is False
        assert get_cipher(backend, stream) is None

        stream = await stream.start_tls(https_server.url.host, ctx, timeout)
        assert stream.is_connection_dropped() is False
        assert get_cipher(backend, stream) is not None

        await stream.write(b"GET / HTTP/1.1\r\n\r\n", timeout)

        response = await read_response(stream, timeout, should_contain=b"Hello, world")
        assert response.startswith(b"HTTP/1.1 200 OK\r\n")

    finally:
        await stream.close()


@pytest.mark.usefixtures("async_environment")
async def test_start_tls_on_uds_socket_stream(https_uds_server):
    backend = lookup_backend()
    ctx = SSLConfig().load_ssl_context_no_verify()
    timeout = Timeout(5)

    stream = await backend.open_uds_stream(
        https_uds_server.config.uds, https_uds_server.url.host, None, timeout
    )

    try:
        assert stream.is_connection_dropped() is False
        assert get_cipher(backend, stream) is None

        stream = await stream.start_tls(https_uds_server.url.host, ctx, timeout)
        assert stream.is_connection_dropped() is False
        assert get_cipher(backend, stream) is not None

        await stream.write(b"GET / HTTP/1.1\r\n\r\n", timeout)

        response = await read_response(stream, timeout, should_contain=b"Hello, world")
        assert response.startswith(b"HTTP/1.1 200 OK\r\n")

    finally:
        await stream.close()


@pytest.mark.usefixtures("async_environment")
async def test_concurrent_read(server):
    """
    Regression test for: https://github.com/encode/httpx/issues/527
    """
    backend = lookup_backend()
    stream = await backend.open_tcp_stream(
        server.url.host, server.url.port, ssl_context=None, timeout=Timeout(5)
    )
    timeout = Timeout(5)
    try:
        await stream.write(b"GET / HTTP/1.1\r\n\r\n", timeout)
        await run_concurrently(
            backend, lambda: stream.read(10, timeout), lambda: stream.read(10, timeout)
        )
    finally:
        await stream.close()


def test_lookup_backend():
    assert isinstance(lookup_backend("asyncio"), AsyncioBackend)
    assert isinstance(lookup_backend("trio"), TrioBackend)
    assert isinstance(lookup_backend(AsyncioBackend()), AsyncioBackend)

    async def get_backend_from_auto():
        auto_backend = lookup_backend("auto")
        return auto_backend.backend

    loop = asyncio.get_event_loop()
    backend = loop.run_until_complete(get_backend_from_auto())
    assert isinstance(backend, AsyncioBackend)

    backend = trio.run(get_backend_from_auto)
    assert isinstance(backend, TrioBackend)

    with pytest.raises(Exception, match="unknownio"):
        lookup_backend("unknownio")
