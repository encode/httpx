import pytest

from httpx._core import (
    AsyncHTTP11Connection,
    ConnectionNotAvailable,
    Origin,
    RawRequest,
    RawURL,
)
from httpx._core.backends.mock import AsyncMockStream


@pytest.mark.trio
async def test_http11_connection():
    origin = Origin(b"https", b"example.com", 443)
    stream = AsyncMockStream(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )
    async with AsyncHTTP11Connection(
        origin=origin, stream=stream, keepalive_expiry=5.0
    ) as conn:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])
        async with await conn.handle_async_request(request) as response:
            content = await response.stream.aread()
            assert response.status == 200
            assert content == b"Hello, world!"

        assert conn.get_origin() == origin
        assert conn.is_idle()
        assert not conn.is_closed()
        assert conn.is_available()
        assert not conn.has_expired()
        assert repr(conn) == "<AsyncHTTP11Connection [IDLE, Request Count: 1]>"


@pytest.mark.trio
async def test_http11_connection_unread_response():
    """
    If the client releases the response without reading it to termination,
    then the connection will not be reusable.
    """
    origin = Origin(b"https", b"example.com", 443)
    stream = AsyncMockStream(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )
    async with AsyncHTTP11Connection(
        origin=origin, stream=stream, keepalive_expiry=5.0
    ) as conn:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])
        async with await conn.handle_async_request(request) as response:
            assert response.status == 200

        assert conn.get_origin() == origin
        assert not conn.is_idle()
        assert conn.is_closed()
        assert not conn.is_available()
        assert not conn.has_expired()
        assert repr(conn) == "<AsyncHTTP11Connection [CLOSED, Request Count: 1]>"


@pytest.mark.trio
async def test_http11_connection_with_network_error():
    """
    If a network error occurs, then no response will be returned, and the
    connection will not be reusable.
    """
    origin = Origin(b"https", b"example.com", 443)
    stream = AsyncMockStream([b"Wait, this isn't valid HTTP!"])
    async with AsyncHTTP11Connection(
        origin=origin, stream=stream, keepalive_expiry=5.0
    ) as conn:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])
        with pytest.raises(Exception):
            await conn.handle_async_request(request)

        assert conn.get_origin() == origin
        assert not conn.is_idle()
        assert conn.is_closed()
        assert not conn.is_available()
        assert not conn.has_expired()
        assert repr(conn) == "<AsyncHTTP11Connection [CLOSED, Request Count: 1]>"


@pytest.mark.trio
async def test_http11_connection_handles_one_active_request():
    """
    Attempting to send a request while one is already in-flight will raise
    a ConnectionNotAvailable exception.
    """
    origin = Origin(b"https", b"example.com", 443)
    stream = AsyncMockStream(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )
    async with AsyncHTTP11Connection(
        origin=origin, stream=stream, keepalive_expiry=5.0
    ) as conn:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])
        async with await conn.handle_async_request(request):
            with pytest.raises(ConnectionNotAvailable):
                await conn.handle_async_request(request)


@pytest.mark.trio
async def test_http11_connection_attempt_close():
    """
    A connection can only be closed when it is idle.
    """
    origin = Origin(b"https", b"example.com", 443)
    stream = AsyncMockStream(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )
    async with AsyncHTTP11Connection(
        origin=origin, stream=stream, keepalive_expiry=5.0
    ) as conn:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])
        async with await conn.handle_async_request(request) as response:
            content = await response.stream.aread()
            assert response.status == 200
            assert content == b"Hello, world!"
            assert not await conn.attempt_close()
        assert await conn.attempt_close()
