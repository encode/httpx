import pytest

import httpx
from httpx.config import SSLConfig
from httpx.dispatch.connection import HTTPConnection


@pytest.mark.usefixtures("async_environment")
async def test_get(server):
    async with HTTPConnection(origin=server.url) as conn:
        response = await conn.request("GET", server.url)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b"Hello, world!"


@pytest.mark.usefixtures("async_environment")
async def test_post(server):
    async with HTTPConnection(origin=server.url) as conn:
        response = await conn.request("GET", server.url, data=b"Hello, world!")
        assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_premature_close(server):
    with pytest.raises(httpx.ConnectionClosed):
        async with HTTPConnection(origin=server.url) as conn:
            response = await conn.request(
                "GET", server.url.copy_with(path="/premature_close")
            )
            await response.aread()


@pytest.mark.usefixtures("async_environment")
async def test_https_get_with_ssl(https_server, ca_cert_pem_file):
    """
    An HTTPS request, with SSL configuration set on the client.
    """
    ssl = SSLConfig(verify=ca_cert_pem_file)
    async with HTTPConnection(origin=https_server.url, ssl=ssl) as conn:
        response = await conn.request("GET", https_server.url)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b"Hello, world!"
