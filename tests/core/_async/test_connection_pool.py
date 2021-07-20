from typing import List

import pytest
import trio as concurrency

from httpx._core import AsyncConnectionPool, RawRequest, RawURL
from httpx._core.backends.mock import AsyncMockBackend


@pytest.mark.trio
async def test_connection_pool_with_keepalive():
    """
    By default HTTP/1.1 requests should be returned to the connection pool.
    """
    network_backend = AsyncMockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    async with AsyncConnectionPool(
        max_connections=10,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])

        # Sending an intial request, which once complete will return to the pool, IDLE.
        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = await response.stream.aread()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = await pool.pool_info()
        assert info == ["'https://example.com:443', HTTP/1.1, IDLE, Request Count: 1"]

        # Sending a second request to the same origin will reuse the existing IDLE connection.
        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 2"
            ]
            body = await response.stream.aread()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = await pool.pool_info()
        assert info == ["'https://example.com:443', HTTP/1.1, IDLE, Request Count: 2"]

        # Sending a request to a different origin will not reuse the existing IDLE connection.
        url = RawURL(b"http", b"example.com", 80, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])

        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            assert info == [
                "'http://example.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
                "'https://example.com:443', HTTP/1.1, IDLE, Request Count: 2",
            ]
            body = await response.stream.aread()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = await pool.pool_info()
        assert info == [
            "'http://example.com:80', HTTP/1.1, IDLE, Request Count: 1",
            "'https://example.com:443', HTTP/1.1, IDLE, Request Count: 2",
        ]


@pytest.mark.trio
async def test_connection_pool_with_close():
    """
    HTTP/1.1 requests that include a 'Connection: Close' header should
    not be returned to the connection pool.
    """
    network_backend = AsyncMockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    async with AsyncConnectionPool(
        max_connections=10,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com"), (b"Connection", b"close")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = await response.stream.aread()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = await pool.pool_info()
        assert info == []


@pytest.mark.trio
async def test_connection_pool_with_exception():
    """
    HTTP/1.1 requests that result in an exception should not be returned to the
    connection pool.
    """
    network_backend = AsyncMockBackend([b"Wait, this isn't valid HTTP!"])

    async with AsyncConnectionPool(
        max_connections=10,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        with pytest.raises(Exception):
            async with await pool.handle_async_request(request):
                pass  # pragma: nocover

        info = await pool.pool_info()
        assert info == []


@pytest.mark.trio
async def test_connection_pool_with_immediate_expiry():
    """
    Connection pools with keepalive_expiry=0.0 should immediately expire
    keep alive connections.
    """
    network_backend = AsyncMockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    async with AsyncConnectionPool(
        max_connections=10,
        keepalive_expiry=0.0,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = await response.stream.aread()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = await pool.pool_info()
        assert info == []


@pytest.mark.trio
async def test_connection_pool_with_no_keepalive_connections_allowed():
    """
    When 'max_keepalive_connections=0' is used, IDLE connections should not
    be returned to the pool.
    """
    network_backend = AsyncMockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    async with AsyncConnectionPool(
        max_connections=10, max_keepalive_connections=0, network_backend=network_backend
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = await response.stream.aread()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = await pool.pool_info()
        assert info == []


@pytest.mark.trio
async def test_connection_pool_concurrency():
    """
    HTTP/1.1 requests made in concurrency must not ever exceed the maximum number
    of allowable connection in the pool.
    """
    network_backend = AsyncMockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    async def fetch(pool, domain, info_list):
        url = RawURL(b"http", domain, 80, b"/")
        headers = [(b"Host", domain)]
        request = RawRequest(b"GET", url, headers)
        async with await pool.handle_async_request(request) as response:
            info = await pool.pool_info()
            info_list.append(info)
            await response.stream.aread()

    async with AsyncConnectionPool(
        max_connections=1, network_backend=network_backend
    ) as pool:
        info_list: List[List[str]] = []
        async with concurrency.open_nursery() as nursery:
            for domain in [b"a.com", b"b.com", b"c.com", b"d.com", b"e.com"]:
                nursery.start_soon(fetch, pool, domain, info_list)

        # Check that each time we inspect the connection pool, only a
        # single connection was established.
        for item in info_list:
            assert len(item) == 1
            assert item[0] in [
                "'http://a.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
                "'http://b.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
                "'http://c.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
                "'http://d.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
                "'http://e.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
            ]
