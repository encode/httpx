from datetime import timedelta

import pytest

import httpx


@pytest.mark.usefixtures("async_environment")
async def test_get(server):
    url = server.url
    async with httpx.AsyncClient(http2=True) as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response [200 OK]>"
    assert response.elapsed > timedelta(seconds=0)

    with pytest.raises(httpx.NotRedirectResponse):
        await response.anext()


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("invalid://example.org", id="scheme-not-http(s)"),
        pytest.param("://example.org", id="no-scheme"),
        pytest.param("http://", id="no-host"),
    ],
)
@pytest.mark.usefixtures("async_environment")
async def test_get_invalid_url(server, url):
    async with httpx.AsyncClient() as client:
        with pytest.raises((httpx.UnsupportedProtocol, httpx.LocalProtocolError)):
            await client.get(url)


@pytest.mark.usefixtures("async_environment")
async def test_build_request(server):
    url = server.url.copy_with(path="/echo_headers")
    headers = {"Custom-header": "value"}
    async with httpx.AsyncClient() as client:
        request = client.build_request("GET", url)
        request.headers.update(headers)
        response = await client.send(request)

    assert response.status_code == 200
    assert response.url == url

    assert response.json()["Custom-header"] == "value"


@pytest.mark.usefixtures("async_environment")
async def test_post(server):
    url = server.url
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_post_json(server):
    url = server.url
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={"text": "Hello, world!"})
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_stream_response(server):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", server.url) as response:
            body = await response.aread()

    assert response.status_code == 200
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


@pytest.mark.usefixtures("async_environment")
async def test_access_content_stream_response(server):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", server.url) as response:
            pass

    assert response.status_code == 200
    with pytest.raises(httpx.ResponseNotRead):
        response.content


@pytest.mark.usefixtures("async_environment")
async def test_stream_request(server):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpx.AsyncClient() as client:
        response = await client.request("POST", server.url, data=hello_world())
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_raise_for_status(server):
    async with httpx.AsyncClient() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", server.url.copy_with(path=f"/status/{status_code}")
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None  # type: ignore


@pytest.mark.usefixtures("async_environment")
async def test_options(server):
    async with httpx.AsyncClient() as client:
        response = await client.options(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.usefixtures("async_environment")
async def test_head(server):
    async with httpx.AsyncClient() as client:
        response = await client.head(server.url)
    assert response.status_code == 200
    assert response.text == ""


@pytest.mark.usefixtures("async_environment")
async def test_put(server):
    async with httpx.AsyncClient() as client:
        response = await client.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_patch(server):
    async with httpx.AsyncClient() as client:
        response = await client.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_delete(server):
    async with httpx.AsyncClient() as client:
        response = await client.delete(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.usefixtures("async_environment")
async def test_100_continue(server):
    headers = {"Expect": "100-continue"}
    data = b"Echo request body"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            server.url.copy_with(path="/echo_body"), headers=headers, data=data
        )

    assert response.status_code == 200
    assert response.content == data


@pytest.mark.usefixtures("async_environment")
async def test_unclosed_client_caused_warning():
    with pytest.warns(ResourceWarning):
        client = httpx.AsyncClient()
        del client

    with pytest.warns(None) as wb:

        async with httpx.AsyncClient() as client:  # noqa: F841
            pass

        assert len(wb.list) == 0


@pytest.mark.usefixtures("async_environment")
async def test_that_client_is_closed_after_with_block():
    async with httpx.AsyncClient() as client:
        pass

    assert client._is_closed
