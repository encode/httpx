import pytest

import httpcore


@pytest.mark.asyncio
async def test_request():
    response = await httpcore.request("GET", "http://example.com")
    assert response.status_code == 200
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_read_response():
    response = await httpcore.request("GET", "http://example.com")

    assert response.status_code == 200
    assert response.body == b"Hello, world!"
    assert response.is_closed

    body = await response.read()

    assert body == b"Hello, world!"
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_stream_response():
    response = await httpcore.request("GET", "http://example.com")

    assert response.status_code == 200
    assert response.body == b"Hello, world!"
    assert response.is_closed

    body = b''
    async for part in response.stream():
        body += part

    assert body == b"Hello, world!"
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_read_streaming_response():
    response = await httpcore.request("GET", "http://example.com", stream=True)

    assert response.status_code == 200
    assert not hasattr(response, 'body')
    assert not response.is_closed

    body = await response.read()

    assert body == b"Hello, world!"
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_stream_streaming_response():
    response = await httpcore.request("GET", "http://example.com", stream=True)

    assert response.status_code == 200
    assert not hasattr(response, 'body')
    assert not response.is_closed

    body = b''
    async for part in response.stream():
        body += part

    assert body == b"Hello, world!"
    assert not hasattr(response, 'body')
    assert response.is_closed


@pytest.mark.asyncio
async def test_cannot_read_after_stream_consumed():
    response = await httpcore.request("GET", "http://example.com", stream=True)

    body = b''
    async for part in response.stream():
        body += part

    with pytest.raises(httpcore.StreamConsumed):
        await response.read()

@pytest.mark.asyncio
async def test_cannot_read_after_response_closed():
    response = await httpcore.request("GET", "http://example.com", stream=True)

    await response.close()

    with pytest.raises(httpcore.ResponseClosed):
        await response.read()
