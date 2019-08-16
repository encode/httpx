import pytest

import httpx


@pytest.mark.usefixtures("server")
async def test_get(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.protocol == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response [200 OK]>"


@pytest.mark.usefixtures("server")
async def test_post(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.post(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("server")
async def test_post_json(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.post(url, json={"text": "Hello, world!"})
    assert response.status_code == 200


@pytest.mark.usefixtures("server")
async def test_stream_response(backend):
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = await response.read()
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


@pytest.mark.usefixtures("server")
async def test_access_content_stream_response(backend):
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    with pytest.raises(httpx.ResponseNotRead):
        response.content


@pytest.mark.usefixtures("server")
async def test_stream_request(backend):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.request(
            "POST", "http://127.0.0.1:8000/", data=hello_world()
        )
    assert response.status_code == 200


@pytest.mark.usefixtures("server")
async def test_raise_for_status(backend):
    async with httpx.AsyncClient(backend=backend) as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", f"http://127.0.0.1:8000/status/{status_code}"
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpx.exceptions.HTTPError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None


@pytest.mark.usefixtures("server")
async def test_options(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.options(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.usefixtures("server")
async def test_head(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.head(url)
    assert response.status_code == 200
    assert response.text == ""


@pytest.mark.usefixtures("server")
async def test_put(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.put(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("server")
async def test_patch(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.patch(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("server")
async def test_delete(backend):
    url = "http://127.0.0.1:8000/"
    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.delete(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.usefixtures("server")
async def test_100_continue(backend):
    url = "http://127.0.0.1:8000/echo_body"
    headers = {"Expect": "100-continue"}
    data = b"Echo request body"

    async with httpx.AsyncClient(backend=backend) as client:
        response = await client.post(url, headers=headers, data=data)

    assert response.status_code == 200
    assert response.content == data
