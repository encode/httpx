import typing
from datetime import timedelta

import httpcore
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
        response = await client.post(url, content=b"Hello, world!")
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
        response = await client.request("POST", server.url, content=hello_world())
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
        response = await client.put(server.url, content=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_patch(server):
    async with httpx.AsyncClient() as client:
        response = await client.patch(server.url, content=b"Hello, world!")
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
    content = b"Echo request body"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            server.url.copy_with(path="/echo_body"), headers=headers, content=content
        )

    assert response.status_code == 200
    assert response.content == content


@pytest.mark.usefixtures("async_environment")
async def test_context_managed_transport():
    class Transport(httpcore.AsyncHTTPTransport):
        def __init__(self):
            self.events = []

        async def aclose(self):
            # The base implementation of httpcore.AsyncHTTPTransport just
            # calls into `.aclose`, so simple transport cases can just override
            # this method for any cleanup, where more complex cases
            # might want to additionally override `__aenter__`/`__aexit__`.
            self.events.append("transport.aclose")

        async def __aenter__(self):
            await super().__aenter__()
            self.events.append("transport.__aenter__")

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            self.events.append("transport.__aexit__")

    transport = Transport()
    async with httpx.AsyncClient(transport=transport):
        pass

    assert transport.events == [
        "transport.__aenter__",
        "transport.aclose",
        "transport.__aexit__",
    ]


@pytest.mark.usefixtures("async_environment")
async def test_context_managed_transport_and_mount():
    class Transport(httpcore.AsyncHTTPTransport):
        def __init__(self, name: str):
            self.name: str = name
            self.events: typing.List[str] = []

        async def aclose(self):
            # The base implementation of httpcore.AsyncHTTPTransport just
            # calls into `.aclose`, so simple transport cases can just override
            # this method for any cleanup, where more complex cases
            # might want to additionally override `__aenter__`/`__aexit__`.
            self.events.append(f"{self.name}.aclose")

        async def __aenter__(self):
            await super().__aenter__()
            self.events.append(f"{self.name}.__aenter__")

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            self.events.append(f"{self.name}.__aexit__")

    transport = Transport(name="transport")
    mounted = Transport(name="mounted")
    async with httpx.AsyncClient(
        transport=transport, mounts={"http://www.example.org": mounted}
    ):
        pass

    assert transport.events == [
        "transport.__aenter__",
        "transport.aclose",
        "transport.__aexit__",
    ]
    assert mounted.events == [
        "mounted.__aenter__",
        "mounted.aclose",
        "mounted.__aexit__",
    ]


def hello_world(request):
    return httpx.Response(200, text="Hello, world!")


@pytest.mark.usefixtures("async_environment")
async def test_client_closed_state_using_implicit_open():
    client = httpx.AsyncClient(transport=httpx.MockTransport(hello_world))

    assert not client.is_closed
    await client.get("http://example.com")

    assert not client.is_closed
    await client.aclose()

    assert client.is_closed
    with pytest.raises(RuntimeError):
        await client.get("http://example.com")


@pytest.mark.usefixtures("async_environment")
async def test_client_closed_state_using_with_block():
    async with httpx.AsyncClient(transport=httpx.MockTransport(hello_world)) as client:
        assert not client.is_closed
        await client.get("http://example.com")

    assert client.is_closed
    with pytest.raises(RuntimeError):
        await client.get("http://example.com")


@pytest.mark.usefixtures("async_environment")
async def test_deleting_unclosed_async_client_causes_warning():
    client = httpx.AsyncClient(transport=httpx.MockTransport(hello_world))
    await client.get("http://example.com")
    with pytest.warns(UserWarning):
        del client


def unmounted(request: httpx.Request) -> httpx.Response:
    data = {"app": "unmounted"}
    return httpx.Response(200, json=data)


def mounted(request: httpx.Request) -> httpx.Response:
    data = {"app": "mounted"}
    return httpx.Response(200, json=data)


@pytest.mark.usefixtures("async_environment")
async def test_mounted_transport():
    transport = httpx.MockTransport(unmounted)
    mounts = {"custom://": httpx.MockTransport(mounted)}

    async with httpx.AsyncClient(transport=transport, mounts=mounts) as client:
        response = await client.get("https://www.example.com")
        assert response.status_code == 200
        assert response.json() == {"app": "unmounted"}

        response = await client.get("custom://www.example.com")
        assert response.status_code == 200
        assert response.json() == {"app": "mounted"}
