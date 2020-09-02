import typing

import httpcore

import httpx
from httpx._content_streams import ContentStream, JSONStream


class MockTransport(httpcore.SyncHTTPTransport):
    def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        timeout: typing.Mapping[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        body = JSONStream({"ok": "ok"})
        return b"HTTP/1.1", 200, b"OK", [], body


def test_client_queryparams():
    client = httpx.Client(params={"a": "b"})
    assert isinstance(client.params, httpx.QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_string():
    client = httpx.Client(params="a=b")
    assert isinstance(client.params, httpx.QueryParams)
    assert client.params["a"] == "b"

    client = httpx.Client()
    client.params = "a=b"  # type: ignore
    assert isinstance(client.params, httpx.QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_echo():
    url = "http://example.org/echo_queryparams"
    client_queryparams = "first=str"
    request_queryparams = {"second": "dict"}
    client = httpx.Client(transport=MockTransport(), params=client_queryparams)
    response = client.get(url, params=request_queryparams)

    assert response.status_code == 200
    assert response.url == "http://example.org/echo_queryparams?first=str&second=dict"
