from datetime import timedelta

import httpcore
import pytest

import httpx
from httpx import ASGIDispatch


@pytest.mark.usefixtures("async_environment")
async def test_get(server):
    url = server.url
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response [200 OK]>"
    assert response.elapsed > timedelta(seconds=0)


@pytest.mark.usefixtures("async_environment")
async def test_get_invalid_url(server):
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.InvalidURL):
            await client.get("invalid://example.org")


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
                with pytest.raises(httpx.HTTPError) as exc_info:
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


def test_dispatch_deprecated():
    dispatch = httpcore.AsyncHTTPTransport()

    with pytest.warns(DeprecationWarning) as record:
        client = httpx.AsyncClient(dispatch=dispatch)

    assert client.transport is dispatch
    assert len(record) == 1
    assert record[0].message.args[0] == (
        "The dispatch argument is deprecated since v0.13 and will be "
        "removed in a future release, please use 'transport'"
    )


def test_asgi_dispatch_deprecated():
    async def app(scope, receive, send):
        pass

    with pytest.warns(DeprecationWarning) as record:
        ASGIDispatch(app)

    assert len(record) == 1
    assert (
        record[0].message.args[0]
        == "ASGIDispatch is deprecated, please use ASGITransport"
    )
