import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    client = httpcore.Connection(origin="http://127.0.0.1:8000/")
    request = httpcore.Request(method="GET", url="http://127.0.0.1:8000/")
    response = await client.send(request)
    assert response.status_code == 200
    assert response.body == b"Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    client = httpcore.Connection(origin="http://127.0.0.1:8000/")
    request = httpcore.Request(
        method="POST", url="http://127.0.0.1:8000/", body=b"Hello, world!"
    )
    response = await client.send(request)
    assert response.status_code == 200
