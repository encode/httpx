#!/usr/bin/env python3

import typing

import pytest

import httpcore
from httpx import AsyncClient, Headers, __version__
from httpx._content_streams import ContentStream, JSONStream


class MockDispatch(httpcore.AsyncHTTPTransport):
    async def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, int, bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: typing.Dict[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        headers_dict = dict(
            [(key.decode("ascii"), value.decode("ascii")) for key, value in headers]
        )
        body = JSONStream({"headers": headers_dict})
        return b"HTTP/1.1", 200, b"OK", [], body


@pytest.mark.asyncio
async def test_client_header():
    """
    Set a header in the Client.
    """
    url = "http://example.org/echo_headers"
    headers = {"Example-Header": "example-value"}

    client = AsyncClient(dispatch=MockDispatch(), headers=headers)
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "example-header": "example-value",
            "host": "example.org",
            "user-agent": f"python-httpx/{__version__}",
        }
    }


@pytest.mark.asyncio
async def test_header_merge():
    url = "http://example.org/echo_headers"
    client_headers = {"User-Agent": "python-myclient/0.2.1"}
    request_headers = {"X-Auth-Token": "FooBarBazToken"}
    client = AsyncClient(dispatch=MockDispatch(), headers=client_headers)
    response = await client.get(url, headers=request_headers)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": "python-myclient/0.2.1",
            "x-auth-token": "FooBarBazToken",
        }
    }


@pytest.mark.asyncio
async def test_header_merge_conflicting_headers():
    url = "http://example.org/echo_headers"
    client_headers = {"X-Auth-Token": "FooBar"}
    request_headers = {"X-Auth-Token": "BazToken"}
    client = AsyncClient(dispatch=MockDispatch(), headers=client_headers)
    response = await client.get(url, headers=request_headers)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": f"python-httpx/{__version__}",
            "x-auth-token": "BazToken",
        }
    }


@pytest.mark.asyncio
async def test_header_update():
    url = "http://example.org/echo_headers"
    client = AsyncClient(dispatch=MockDispatch())
    first_response = await client.get(url)
    client.headers.update(
        {"User-Agent": "python-myclient/0.2.1", "Another-Header": "AThing"}
    )
    second_response = await client.get(url)

    assert first_response.status_code == 200
    assert first_response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": f"python-httpx/{__version__}",
        }
    }

    assert second_response.status_code == 200
    assert second_response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "another-header": "AThing",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": "python-myclient/0.2.1",
        }
    }


def test_header_does_not_exist():
    headers = Headers({"foo": "bar"})
    with pytest.raises(KeyError):
        del headers["baz"]


@pytest.mark.asyncio
async def test_host_with_auth_and_port_in_url():
    """
    The Host header should only include the hostname, or hostname:port
    (for non-default ports only). Any userinfo or default port should not
    be present.
    """
    url = "http://username:password@example.org:80/echo_headers"

    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": f"python-httpx/{__version__}",
            "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        }
    }


@pytest.mark.asyncio
async def test_host_with_non_default_port_in_url():
    """
    If the URL includes a non-default port, then it should be included in
    the Host header.
    """
    url = "http://username:password@example.org:123/echo_headers"

    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "host": "example.org:123",
            "user-agent": f"python-httpx/{__version__}",
            "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        }
    }
