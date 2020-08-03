import typing

import httpcore
import pytest

from httpx import URL, AsyncClient, QueryParams
from httpx._content_streams import ContentStream, JSONStream


class MockTransport(httpcore.AsyncHTTPTransport):
    async def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: typing.Mapping[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        body = JSONStream({"ok": "ok"})
        return b"HTTP/1.1", 200, b"OK", [], body


def test_client_queryparams():
    client = AsyncClient(params={"a": "b"})
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_string():
    client = AsyncClient(params="a=b")
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"

    client = AsyncClient()
    client.params = "a=b"  # type: ignore
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


@pytest.mark.asyncio
async def test_client_queryparams_echo():
    url = "http://example.org/echo_queryparams"
    client_queryparams = "first=str"
    request_queryparams = {"second": "dict"}
    client = AsyncClient(transport=MockTransport(), params=client_queryparams)
    response = await client.get(url, params=request_queryparams)

    assert response.status_code == 200
    assert response.url == URL(
        "http://example.org/echo_queryparams?first=str&second=dict"
    )
