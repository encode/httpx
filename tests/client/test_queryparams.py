import typing

import pytest

from httpx import URL, AsyncClient, Headers, QueryParams
from httpx._config import TimeoutTypes
from httpx._content_streams import ContentStream, JSONStream
from httpx._dispatch.base import AsyncDispatcher


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        method: bytes,
        url: URL,
        headers: Headers,
        stream: ContentStream,
        timeout: TimeoutTypes = None,
    ) -> typing.Tuple[int, str, Headers, ContentStream]:
        headers = Headers()
        body = JSONStream({"ok": "ok"})
        return 200, "HTTP/1.1", headers, body


def test_client_queryparams():
    client = AsyncClient(params={"a": "b"})
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_string():
    client = AsyncClient(params="a=b")
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"

    client = AsyncClient()
    client.params = "a=b"
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


@pytest.mark.asyncio
async def test_client_queryparams_echo():
    url = "http://example.org/echo_queryparams"
    client_queryparams = "first=str"
    request_queryparams = {"second": "dict"}
    client = AsyncClient(dispatch=MockDispatch(), params=client_queryparams)
    response = await client.get(url, params=request_queryparams)

    assert response.status_code == 200
    assert response.url == URL(
        "http://example.org/echo_queryparams?first=str&second=dict"
    )
