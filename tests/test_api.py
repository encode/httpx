import pytest

import httpx


@pytest.mark.asyncio
async def test_get(server):
    response = await httpx.get(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_post(server):
    response = await httpx.post(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_post_byte_iterator(server):
    async def data():
        yield b"Hello"
        yield b", "
        yield b"world!"

    response = await httpx.post(server.url, data=data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_options(server):
    response = await httpx.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_head(server):
    response = await httpx.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_put(server):
    response = await httpx.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_patch(server):
    response = await httpx.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_delete(server):
    response = await httpx.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_stream(server):
    async with httpx.stream("GET", server.url) as response:
        await response.aread()

    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_get_invalid_url(server):
    with pytest.raises(httpx.InvalidURL):
        await httpx.get("invalid://example.org")
