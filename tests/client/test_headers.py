#!/usr/bin/env python3

import json

from httpx import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    TimeoutTypes,
    VerifyTypes,
    __version__,
)


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        if request.url.path.startswith("/echo_headers"):
            request_headers = dict(request.headers.items())
            body = json.dumps({"headers": request_headers}).encode()
            return AsyncResponse(200, content=body, request=request)


def test_client_header():
    """
    Set a header in the Client.
    """
    url = "http://example.org/echo_headers"
    headers = {"Example-Header": "example-value"}

    with Client(dispatch=MockDispatch(), headers=headers) as client:
        response = client.get(url)

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


def test_header_merge():
    url = "http://example.org/echo_headers"
    client_headers = {"User-Agent": "python-myclient/0.2.1"}
    request_headers = {"X-Auth-Token": "FooBarBazToken"}
    with Client(dispatch=MockDispatch(), headers=client_headers) as client:
        response = client.get(url, headers=request_headers)

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


def test_header_merge_conflicting_headers():
    url = "http://example.org/echo_headers"
    client_headers = {"X-Auth-Token": "FooBar"}
    request_headers = {"X-Auth-Token": "BazToken"}
    with Client(dispatch=MockDispatch(), headers=client_headers) as client:
        response = client.get(url, headers=request_headers)

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


def test_header_update():
    url = "http://example.org/echo_headers"
    with Client(dispatch=MockDispatch()) as client:
        first_response = client.get(url)
        client.headers.update(
            {"User-Agent": "python-myclient/0.2.1", "Another-Header": "AThing"}
        )
        second_response = client.get(url)

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
