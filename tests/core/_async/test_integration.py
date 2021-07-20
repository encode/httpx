import ssl

import pytest

from httpx._core import AsyncConnectionPool, RawRequest, RawURL


@pytest.mark.trio
async def test_request(server):
    async with AsyncConnectionPool() as pool:
        url = RawURL(*server.url.raw)
        request = RawRequest(b"GET", url, [(b"Host", server.url.raw_host)])
        async with await pool.handle_async_request(request) as response:
            assert response.status == 200


@pytest.mark.trio
async def test_https_request(https_server):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with AsyncConnectionPool(ssl_context=ssl_context) as pool:
        url = RawURL(*https_server.url.raw)
        request = RawRequest(b"GET", url, [(b"Host", https_server.url.raw_host)])
        async with await pool.handle_async_request(request) as response:
            assert response.status == 200
