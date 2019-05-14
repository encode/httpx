import pytest

from httpcore import HTTPConnection, Request, SSLConfig


@pytest.mark.asyncio
async def test_get(server):
    conn = HTTPConnection(origin="http://127.0.0.1:8000/")
    request = Request("GET", "http://127.0.0.1:8000/")
    request.prepare()
    response = await conn.send(request)
    assert response.status_code == 200
    assert response.content == b"Hello, world!"


@pytest.mark.asyncio
async def test_https_get(https_server):
    http = HTTPConnection(origin="https://127.0.0.1:8001/", ssl=SSLConfig(verify=False))
    response = await http.request("GET", "https://127.0.0.1:8001/")
    assert response.status_code == 200
    assert response.content == b"Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    conn = HTTPConnection(origin="http://127.0.0.1:8000/")
    request = Request("GET", "http://127.0.0.1:8000/", data=b"Hello, world!")
    request.prepare()
    response = await conn.send(request)
    assert response.status_code == 200
