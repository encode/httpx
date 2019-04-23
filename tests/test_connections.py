import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    http = httpcore.HTTP11Connection(origin="http://127.0.0.1:8000/")
    response = await http.request("GET", "http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.body == b"Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    http = httpcore.HTTP11Connection(origin="http://127.0.0.1:8000/")
    response = await http.request(
        "POST", "http://127.0.0.1:8000/", body=b"Hello, world!"
    )
    assert response.status_code == 200
