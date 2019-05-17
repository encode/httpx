import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.protocol == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response(200, 'OK')>"


@pytest.mark.asyncio
async def test_post(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.post(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_post_json(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.post(url, json={"text": "Hello, world!"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_response(server):
    async with httpcore.AsyncClient() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = await response.read()
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


@pytest.mark.asyncio
async def test_access_content_stream_response(server):
    async with httpcore.AsyncClient() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    with pytest.raises(httpcore.ResponseNotRead):
        response.content


@pytest.mark.asyncio
async def test_stream_request(server):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpcore.AsyncClient() as client:
        response = await client.request(
            "POST", "http://127.0.0.1:8000/", data=hello_world()
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_raise_for_status(server):
    async with httpcore.AsyncClient() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", f"http://127.0.0.1:8000/status/{status_code}"
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpcore.exceptions.HttpError):
                    response.raise_for_status()
            else:
                assert response.raise_for_status() is None


@pytest.mark.asyncio
async def test_options(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.options(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.asyncio
async def test_head(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.head(url)
    assert response.status_code == 200
    assert response.text == ""


@pytest.mark.asyncio
async def test_put(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.put(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_patch(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.patch(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.delete(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.asyncio
async def test_100_continue(server):
    url = "http://127.0.0.1:8000/echo_body"
    headers = {"Expect": "100-continue"}
    data = b"Echo request body"

    async with httpcore.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)

    assert response.status_code == 200
    assert response.content == data
