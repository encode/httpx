#!/usr/bin/env python3

import pytest

import httpx


def echo_headers(request: httpx.Request) -> httpx.Response:
    data = {"headers": dict(request.headers)}
    return httpx.Response(200, json=data)


def echo_repeated_headers_multi_items(request: httpx.Request) -> httpx.Response:
    data = {"headers": list(request.headers.multi_items())}
    return httpx.Response(200, json=data)


def echo_repeated_headers_items(request: httpx.Request) -> httpx.Response:
    data = {"headers": list(request.headers.items())}
    return httpx.Response(200, json=data)


def test_client_header():
    """
    Set a header in the Client.
    """
    url = "http://example.org/echo_headers"
    headers = {"Example-Header": "example-value"}

    client = httpx.Client(transport=httpx.MockTransport(echo_headers), headers=headers)
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "connection": "keep-alive",
            "example-header": "example-value",
            "host": "example.org",
            "user-agent": f"python-httpx/{httpx.__version__}",
        }
    }


def test_header_merge():
    url = "http://example.org/echo_headers"
    client_headers = {"User-Agent": "python-myclient/0.2.1"}
    request_headers = {"X-Auth-Token": "FooBarBazToken"}
    client = httpx.Client(
        transport=httpx.MockTransport(echo_headers), headers=client_headers
    )
    response = client.get(url, headers=request_headers)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
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
    client = httpx.Client(
        transport=httpx.MockTransport(echo_headers), headers=client_headers
    )
    response = client.get(url, headers=request_headers)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": f"python-httpx/{httpx.__version__}",
            "x-auth-token": "BazToken",
        }
    }


def test_header_update():
    url = "http://example.org/echo_headers"
    client = httpx.Client(transport=httpx.MockTransport(echo_headers))
    first_response = client.get(url)
    client.headers.update(
        {"User-Agent": "python-myclient/0.2.1", "Another-Header": "AThing"}
    )
    second_response = client.get(url)

    assert first_response.status_code == 200
    assert first_response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": f"python-httpx/{httpx.__version__}",
        }
    }

    assert second_response.status_code == 200
    assert second_response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "another-header": "AThing",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": "python-myclient/0.2.1",
        }
    }


def test_header_repeated_items():
    url = "http://example.org/echo_headers"
    client = httpx.Client(transport=httpx.MockTransport(echo_repeated_headers_items))
    response = client.get(url, headers=[("x-header", "1"), ("x-header", "2,3")])

    assert response.status_code == 200

    echoed_headers = response.json()["headers"]
    # as per RFC 7230, the whitespace after a comma is insignificant
    # so we split and strip here so that we can do a safe comparison
    assert ["x-header", ["1", "2", "3"]] in [
        [k, [subv.lstrip() for subv in v.split(",")]] for k, v in echoed_headers
    ]


def test_header_repeated_multi_items():
    url = "http://example.org/echo_headers"
    client = httpx.Client(
        transport=httpx.MockTransport(echo_repeated_headers_multi_items)
    )
    response = client.get(url, headers=[("x-header", "1"), ("x-header", "2,3")])

    assert response.status_code == 200

    echoed_headers = response.json()["headers"]
    assert ["x-header", "1"] in echoed_headers
    assert ["x-header", "2,3"] in echoed_headers


def test_remove_default_header():
    """
    Remove a default header from the Client.
    """
    url = "http://example.org/echo_headers"

    client = httpx.Client(transport=httpx.MockTransport(echo_headers))
    del client.headers["User-Agent"]

    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "connection": "keep-alive",
            "host": "example.org",
        }
    }


def test_header_does_not_exist():
    headers = httpx.Headers({"foo": "bar"})
    with pytest.raises(KeyError):
        del headers["baz"]


def test_host_with_auth_and_port_in_url():
    """
    The Host header should only include the hostname, or hostname:port
    (for non-default ports only). Any userinfo or default port should not
    be present.
    """
    url = "http://username:password@example.org:80/echo_headers"

    client = httpx.Client(transport=httpx.MockTransport(echo_headers))
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "connection": "keep-alive",
            "host": "example.org",
            "user-agent": f"python-httpx/{httpx.__version__}",
            "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        }
    }


def test_host_with_non_default_port_in_url():
    """
    If the URL includes a non-default port, then it should be included in
    the Host header.
    """
    url = "http://username:password@example.org:123/echo_headers"

    client = httpx.Client(transport=httpx.MockTransport(echo_headers))
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "connection": "keep-alive",
            "host": "example.org:123",
            "user-agent": f"python-httpx/{httpx.__version__}",
            "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        }
    }


def test_request_auto_headers():
    request = httpx.Request("GET", "https://www.example.org/")
    assert "host" in request.headers
