import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.Client() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.content == b"Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.Client() as client:
        response = await client.post(url, body=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_response(server):
    async with httpcore.Client() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = await response.read()
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


@pytest.mark.asyncio
async def test_access_content_stream_response(server):
    async with httpcore.Client() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    with pytest.raises(httpcore.ResponseNotRead):
        response.content


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
