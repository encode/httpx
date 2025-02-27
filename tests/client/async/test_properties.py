import pytest

import httpx


@pytest.mark.anyio
async def test_client_base_url():
    async with httpx.AsyncClient() as client:
        client.base_url = "https://www.example.org/"  # type: ignore
        assert isinstance(client.base_url, httpx.URL)
        assert client.base_url == "https://www.example.org/"


@pytest.mark.anyio
async def test_client_base_url_without_trailing_slash():
    async with httpx.AsyncClient() as client:
        client.base_url = "https://www.example.org/path"  # type: ignore
        assert isinstance(client.base_url, httpx.URL)
        assert client.base_url == "https://www.example.org/path/"


@pytest.mark.anyio
async def test_client_base_url_with_trailing_slash():
    client = httpx.Client()
    client.base_url = "https://www.example.org/path/"  # type: ignore
    assert isinstance(client.base_url, httpx.URL)
    assert client.base_url == "https://www.example.org/path/"


@pytest.mark.anyio
async def test_client_headers():
    async with httpx.AsyncClient() as client:
        client.headers = {"a": "b"}  # type: ignore
        assert isinstance(client.headers, httpx.Headers)
        assert client.headers["A"] == "b"


@pytest.mark.anyio
async def test_client_cookies():
    async with httpx.AsyncClient() as client:
        client.cookies = {"a": "b"}  # type: ignore
        assert isinstance(client.cookies, httpx.Cookies)
        mycookies = list(client.cookies.jar)
        assert len(mycookies) == 1
        assert mycookies[0].name == "a" and mycookies[0].value == "b"


@pytest.mark.anyio
async def test_client_timeout():
    expected_timeout = 12.0
    async with httpx.AsyncClient() as client:
        client.timeout = expected_timeout  # type: ignore

        assert isinstance(client.timeout, httpx.Timeout)
        assert client.timeout.connect == expected_timeout
        assert client.timeout.read == expected_timeout
        assert client.timeout.write == expected_timeout
        assert client.timeout.pool == expected_timeout


@pytest.mark.anyio
async def test_client_event_hooks():
    def on_request(request):
        pass  # pragma: no cover

    async with httpx.AsyncClient() as client:
        client.event_hooks = {"request": [on_request]}
        assert client.event_hooks == {"request": [on_request], "response": []}


@pytest.mark.anyio
async def test_client_trust_env():
    async with httpx.AsyncClient() as client:
        assert client.trust_env

    async with httpx.AsyncClient(trust_env=False) as client:
        assert not client.trust_env
