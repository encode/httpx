import pytest

import httpcore


async def streaming_body():
    yield b"Hello, "
    yield b"world!"


def test_response():
    response = httpcore.Response(200, body=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason == "OK"
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_read_response():
    response = httpcore.Response(200, body=b"Hello, world!")

    assert response.status_code == 200
    assert response.body == b"Hello, world!"
    assert response.is_closed

    body = await response.read()

    assert body == b"Hello, world!"
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_streaming_response():
    response = httpcore.Response(200, body=streaming_body())

    assert response.status_code == 200
    assert not hasattr(response, "body")
    assert not response.is_closed

    body = await response.read()

    assert body == b"Hello, world!"
    assert response.body == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_cannot_read_after_stream_consumed():
    response = httpcore.Response(200, body=streaming_body())

    body = b""
    async for part in response.stream():
        body += part

    with pytest.raises(httpcore.StreamConsumed):
        await response.read()


@pytest.mark.asyncio
async def test_cannot_read_after_response_closed():
    response = httpcore.Response(200, body=streaming_body())

    await response.close()

    with pytest.raises(httpcore.ResponseClosed):
        await response.read()


def test_unknown_status_code():
    response = httpcore.Response(600)
    assert response.status_code == 600
    assert response.reason == ""
