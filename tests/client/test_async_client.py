from datetime import timedelta

import pytest

import httpx


async def test_get(server, backend):
    url = server.url
    async with httpx.Client() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response [200 OK]>"
    assert response.elapsed > timedelta(seconds=0)


async def test_build_request(server, backend):
    url = server.url.copy_with(path="/echo_headers")
    headers = {"Custom-header": "value"}
    async with httpx.Client() as client:
        request = client.build_request("GET", url)
        request.headers.update(headers)
        response = await client.send(request)

    assert response.status_code == 200
    assert response.url == url

    assert response.json()["Custom-header"] == "value"


@pytest.mark.asyncio
async def test_get_no_backend(server):
    """
    Verify that the client is capable of making a simple request if not given a backend.
    """
    url = server.url
    async with httpx.Client() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response [200 OK]>"


async def test_post(server, backend):
    url = server.url
    async with httpx.Client() as client:
        response = await client.post(url, data=b"Hello, world!")
    assert response.status_code == 200


async def test_post_json(server, backend):
    url = server.url
    async with httpx.Client() as client:
        response = await client.post(url, json={"text": "Hello, world!"})
    assert response.status_code == 200


async def test_stream_response(server, backend):
    async with httpx.Client() as client:
        async with client.stream("GET", server.url) as response:
            body = await response.aread()

    assert response.status_code == 200
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


async def test_access_content_stream_response(server, backend):
    async with httpx.Client() as client:
        async with client.stream("GET", server.url) as response:
            pass

    assert response.status_code == 200
    with pytest.raises(httpx.ResponseNotRead):
        response.content


async def test_stream_request(server, backend):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpx.Client() as client:
        response = await client.request("POST", server.url, data=hello_world())
    assert response.status_code == 200


async def test_raise_for_status(server, backend):
    async with httpx.Client() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", server.url.copy_with(path=f"/status/{status_code}")
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpx.HTTPError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None


async def test_options(server, backend):
    async with httpx.Client() as client:
        response = await client.options(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


async def test_head(server, backend):
    async with httpx.Client() as client:
        response = await client.head(server.url)
    assert response.status_code == 200
    assert response.text == ""


async def test_put(server, backend):
    async with httpx.Client() as client:
        response = await client.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200


async def test_patch(server, backend):
    async with httpx.Client() as client:
        response = await client.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200


async def test_delete(server, backend):
    async with httpx.Client() as client:
        response = await client.delete(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


async def test_100_continue(server, backend):
    headers = {"Expect": "100-continue"}
    data = b"Echo request body"

    async with httpx.Client() as client:
        response = await client.post(
            server.url.copy_with(path="/echo_body"), headers=headers, data=data
        )

    assert response.status_code == 200
    assert response.content == data


async def test_uds(uds_server, backend):
    url = uds_server.url
    uds = uds_server.config.uds
    assert uds is not None
    async with httpx.Client(uds=uds) as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.encoding == "iso-8859-1"


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("asyncio", marks=pytest.mark.asyncio),
        pytest.param("trio", marks=pytest.mark.trio),
    ],
)
async def test_explicit_backend(server, backend):
    async with httpx.Client(backend=backend) as client:
        response = await client.get(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
