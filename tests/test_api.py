import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    async with httpcore.Client() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.body == b"Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    async with httpcore.Client() as client:
        response = await client.request(
            "POST", "http://127.0.0.1:8000/", body=b"Hello, world!"
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_response(server):
    async with httpcore.Client() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    assert not hasattr(response, "body")
    body = await response.read()
    assert body == b"Hello, world!"


@pytest.mark.asyncio
async def test_stream_request(server):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpcore.Client() as client:
        response = await client.request(
            "POST", "http://127.0.0.1:8000/", body=hello_world()
        )
    assert response.status_code == 200
