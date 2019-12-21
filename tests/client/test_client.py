from datetime import timedelta

import pytest

import httpx


@pytest.mark.asyncio
async def test_get(server):
    url = server.url
    async with httpx.Client() as http:
        response = await http.get(url)
    assert response.status_code == 200
    assert response.url == url
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.encoding == "iso-8859-1"
    assert response.request.url == url
    assert response.headers
    assert response.is_redirect is False
    assert repr(response) == "<Response [200 OK]>"
    assert response.elapsed > timedelta(0)


@pytest.mark.asyncio
async def test_build_request(server):
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
async def test_post(server):
    async with httpx.Client() as client:
        response = await client.post(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_post_json(server):
    async with httpx.Client() as client:
        response = await client.post(server.url, json={"text": "Hello, world!"})
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_stream_response(server):
    async with httpx.Client() as client:
        async with client.stream("GET", server.url) as response:
            content = await response.aread()
    assert response.status_code == 200
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_stream_iterator(server):
    body = b""

    async with httpx.Client() as client:
        async with client.stream("GET", server.url) as response:
            async for chunk in response.aiter_bytes():
                body += chunk

    assert response.status_code == 200
    assert body == b"Hello, world!"


@pytest.mark.asyncio
async def test_raw_iterator(server):
    body = b""

    async with httpx.Client() as client:
        async with client.stream("GET", server.url) as response:
            async for chunk in response.aiter_raw():
                body += chunk

    assert response.status_code == 200
    assert body == b"Hello, world!"


@pytest.mark.asyncio
async def test_raise_for_status(server):
    async with httpx.Client() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", server.url.copy_with(path="/status/{}".format(status_code))
            )
            if 400 <= status_code < 600:
                with pytest.raises(httpx.HTTPError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None


@pytest.mark.asyncio
async def test_options(server):
    async with httpx.Client() as client:
        response = await client.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_head(server):
    async with httpx.Client() as client:
        response = await client.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_put(server):
    async with httpx.Client() as client:
        response = await client.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_patch(server):
    async with httpx.Client() as client:
        response = await client.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_delete(server):
    async with httpx.Client() as client:
        response = await client.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.asyncio
async def test_base_url(server):
    base_url = server.url
    async with httpx.Client(base_url=base_url) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.url == base_url


@pytest.mark.asyncio
async def test_uds(uds_server):
    url = uds_server.url
    uds = uds_server.config.uds
    assert uds is not None
    async with httpx.Client(uds=uds) as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.encoding == "iso-8859-1"


def test_merge_url():
    client = httpx.Client(base_url="https://www.paypal.com/")
    url = client.merge_url("http://www.paypal.com")

    assert url.scheme == "https"
    assert url.is_ssl


@pytest.mark.asyncio
async def test_elapsed_delay(server):
    url = server.url.copy_with(path="/slow_response/100")
    async with httpx.Client() as client:
        response = await client.get(url)
    assert response.elapsed.total_seconds() > 0.0
