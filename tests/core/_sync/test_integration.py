import ssl

import pytest

from httpx._core import ConnectionPool, RawRequest, RawURL



def test_request(server):
    with ConnectionPool() as pool:
        url = RawURL(*server.url.raw)
        request = RawRequest(b"GET", url, [(b"Host", server.url.raw_host)])
        with pool.handle_request(request) as response:
            assert response.status == 200



def test_https_request(https_server):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    with ConnectionPool(ssl_context=ssl_context) as pool:
        url = RawURL(*https_server.url.raw)
        request = RawRequest(b"GET", url, [(b"Host", https_server.url.raw_host)])
        with pool.handle_request(request) as response:
            assert response.status == 200
