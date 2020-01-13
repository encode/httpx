#!/usr/bin/env python3

import json

import pytest

from httpx import AsyncClient, Headers, Request, Response, __version__
from httpx.config import CertTypes, TimeoutTypes, VerifyTypes
from httpx.dispatch.base import AsyncDispatcher


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        if request.url.path.startswith("/echo_headers"):
            request_headers = dict(request.headers.items())
            body = json.dumps({"headers": request_headers}).encode()
            return Response(200, content=body, request=request)


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
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Example-Header": "example-value",
            "Host": "example.org",
            "User-Agent": f"python-httpx/{__version__}",
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
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Host": "example.org",
            "User-Agent": "python-myclient/0.2.1",
            "X-Auth-Token": "FooBarBazToken",
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
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Host": "example.org",
            "User-Agent": f"python-httpx/{__version__}",
            "X-Auth-Token": "BazToken",
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
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Host": "example.org",
            "User-Agent": f"python-httpx/{__version__}",
        }
    }

    assert second_response.status_code == 200
    assert second_response.json() == {
        "headers": {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Another-Header": "AThing",
            "Connection": "keep-alive",
            "Host": "example.org",
            "User-Agent": "python-myclient/0.2.1",
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
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Host": "example.org",
            "User-Agent": f"python-httpx/{__version__}",
            "Authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
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
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Host": "example.org:123",
            "User-Agent": f"python-httpx/{__version__}",
            "Authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        }
    }
