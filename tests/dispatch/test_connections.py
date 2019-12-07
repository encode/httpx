import pytest

import httpx
from httpx.dispatch.connection import HTTPConnection


async def test_get(server, backend):
    async with HTTPConnection(origin=server.url) as conn:
        response = await conn.request("GET", server.url)
        await response.read()
        assert response.status_code == 200
        assert response.content == b"Hello, world!"


async def test_post(server, backend):
    async with HTTPConnection(origin=server.url) as conn:
        response = await conn.request("GET", server.url, data=b"Hello, world!")
        assert response.status_code == 200


async def test_premature_close(server, backend):
    with pytest.raises(httpx.ConnectionClosed):
        async with HTTPConnection(origin=server.url) as conn:
            response = await conn.request(
                "GET", server.url.copy_with(path="/premature_close")
            )
            await response.read()


async def test_https_get_with_ssl(https_server, ca_cert_pem_file, backend):
    """
    An HTTPS request, with SSL configuration set on the client.
    """
    async with HTTPConnection(origin=https_server.url, verify=ca_cert_pem_file) as conn:
        response = await conn.request("GET", https_server.url)
        await response.read()
        assert response.status_code == 200
        assert response.content == b"Hello, world!"
