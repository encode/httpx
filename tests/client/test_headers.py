#!/usr/bin/env python3

import json

import pytest

from httpx import Client, Headers, Request, Response, __version__
from httpx.config import CertTypes, TimeoutTypes, VerifyTypes
from httpx.dispatch.base import Dispatcher


class MockDispatch(Dispatcher):
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

    client = Client(dispatch=MockDispatch(), headers=headers)
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
    client = Client(dispatch=MockDispatch(), headers=client_headers)
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
    client = Client(dispatch=MockDispatch(), headers=client_headers)
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
    client = Client(dispatch=MockDispatch())
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
async def test_host_without_auth_in_header():
    url = "http://username:password@example.org:80/echo_headers"

    client = Client(dispatch=MockDispatch())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "host": "example.org:80",
            "user-agent": f"python-httpx/{__version__}",
            "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        }
    }
