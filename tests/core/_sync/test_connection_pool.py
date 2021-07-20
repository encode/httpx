from typing import List

import pytest
from tests.core import concurrency

from httpx._core import ConnectionPool, RawRequest, RawURL
from httpx._core.backends.mock import MockBackend



def test_connection_pool_with_keepalive():
    """
    By default HTTP/1.1 requests should be returned to the connection pool.
    """
    network_backend = MockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    with ConnectionPool(
        max_connections=10,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])

        # Sending an intial request, which once complete will return to the pool, IDLE.
        with pool.handle_request(request) as response:
            info = pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = response.stream.read()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = pool.pool_info()
        assert info == ["'https://example.com:443', HTTP/1.1, IDLE, Request Count: 1"]

        # Sending a second request to the same origin will reuse the existing IDLE connection.
        with pool.handle_request(request) as response:
            info = pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 2"
            ]
            body = response.stream.read()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = pool.pool_info()
        assert info == ["'https://example.com:443', HTTP/1.1, IDLE, Request Count: 2"]

        # Sending a request to a different origin will not reuse the existing IDLE connection.
        url = RawURL(b"http", b"example.com", 80, b"/")
        request = RawRequest(b"GET", url, [(b"Host", b"example.com")])

        with pool.handle_request(request) as response:
            info = pool.pool_info()
            assert info == [
                "'http://example.com:80', HTTP/1.1, ACTIVE, Request Count: 1",
                "'https://example.com:443', HTTP/1.1, IDLE, Request Count: 2",
            ]
            body = response.stream.read()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = pool.pool_info()
        assert info == [
            "'http://example.com:80', HTTP/1.1, IDLE, Request Count: 1",
            "'https://example.com:443', HTTP/1.1, IDLE, Request Count: 2",
        ]



def test_connection_pool_with_close():
    """
    HTTP/1.1 requests that include a 'Connection: Close' header should
    not be returned to the connection pool.
    """
    network_backend = MockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    with ConnectionPool(
        max_connections=10,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com"), (b"Connection", b"close")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        with pool.handle_request(request) as response:
            info = pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = response.stream.read()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = pool.pool_info()
        assert info == []



def test_connection_pool_with_exception():
    """
    HTTP/1.1 requests that result in an exception should not be returned to the
    connection pool.
    """
    network_backend = MockBackend([b"Wait, this isn't valid HTTP!"])

    with ConnectionPool(
        max_connections=10,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        with pytest.raises(Exception):
            with pool.handle_request(request):
                pass  # pragma: nocover

        info = pool.pool_info()
        assert info == []



def test_connection_pool_with_immediate_expiry():
    """
    Connection pools with keepalive_expiry=0.0 should immediately expire
    keep alive connections.
    """
    network_backend = MockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    with ConnectionPool(
        max_connections=10,
        keepalive_expiry=0.0,
        network_backend=network_backend,
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        with pool.handle_request(request) as response:
            info = pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = response.stream.read()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = pool.pool_info()
        assert info == []



def test_connection_pool_with_no_keepalive_connections_allowed():
    """
    When 'max_keepalive_connections=0' is used, IDLE connections should not
    be returned to the pool.
    """
    network_backend = MockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    with ConnectionPool(
        max_connections=10, max_keepalive_connections=0, network_backend=network_backend
    ) as pool:
        url = RawURL(b"https", b"example.com", 443, b"/")
        headers = [(b"Host", b"example.com")]
        request = RawRequest(b"GET", url, headers)

        # Sending an intial request, which once complete will not return to the pool.
        with pool.handle_request(request) as response:
            info = pool.pool_info()
            assert info == [
                "'https://example.com:443', HTTP/1.1, ACTIVE, Request Count: 1"
            ]
            body = response.stream.read()

        assert response.status == 200
        assert body == b"Hello, world!"
        info = pool.pool_info()
        assert info == []



def test_connection_pool_concurrency():
    """
    HTTP/1.1 requests made in concurrency must not ever exceed the maximum number
    of allowable connection in the pool.
    """
    network_backend = MockBackend(
        [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: plain/text\r\n",
            b"Content-Length: 13\r\n",
            b"\r\n",
            b"Hello, world!",
        ]
    )

    def fetch(pool, domain, info_list):
        url = RawURL(b"http", domain, 80, b"/")
        headers = [(b"Host", domain)]
        request = RawRequest(b"GET", url, headers)
        with pool.handle_request(request) as response:
            info = pool.pool_info()
            info_list.append(info)
            response.stream.read()

    with ConnectionPool(
        max_connections=1, network_backend=network_backend
    ) as pool:
        info_list: List[List[str]] = []
        with concurrency.open_nursery() as nursery:
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
