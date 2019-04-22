import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    async with httpcore.ConnectionPool() as client:
        request = httpcore.Request("GET", "http://127.0.0.1:8000/")
        response = await client.send(request)
    assert response.status_code == 200
    assert response.body == b"Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    async with httpcore.ConnectionPool() as client:
        request = httpcore.Request(
            "POST", "http://127.0.0.1:8000/", body=b"Hello, world!"
        )
        response = await client.send(request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_response(server):
    async with httpcore.ConnectionPool() as client:
        request = httpcore.Request("GET", "http://127.0.0.1:8000/")
        response = await client.send(request, stream=True)
    assert response.status_code == 200
    assert not hasattr(response, "body")
    body = await response.read()
    assert body == b"Hello, world!"


@pytest.mark.asyncio
async def test_stream_request(server):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpcore.ConnectionPool() as client:
        request = httpcore.Request("POST", "http://127.0.0.1:8000/", body=hello_world())
        response = await client.send(request)
    assert response.status_code == 200
