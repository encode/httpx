import pytest

import httpx


def hello_world(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="Hello, world")


@pytest.mark.anyio
async def test_client_queryparams():
    client = httpx.Client(params={"a": "b"})
    assert isinstance(client.params, httpx.QueryParams)
    assert client.params["a"] == "b"


@pytest.mark.anyio
async def test_client_queryparams_string():
    async with httpx.AsyncClient(params="a=b") as client:
        assert isinstance(client.params, httpx.QueryParams)
        assert client.params["a"] == "b"

    async with httpx.AsyncClient() as client:
        client.params = "a=b"  # type: ignore
        assert isinstance(client.params, httpx.QueryParams)
        assert client.params["a"] == "b"


@pytest.mark.anyio
async def test_client_queryparams_echo():
    url = "http://example.org/echo_queryparams"
    client_queryparams = "first=str"
    request_queryparams = {"second": "dict"}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(hello_world), params=client_queryparams
    ) as client:
        response = await client.get(url, params=request_queryparams)

        assert response.status_code == 200
        assert (
            response.url == "http://example.org/echo_queryparams?first=str&second=dict"
        )
