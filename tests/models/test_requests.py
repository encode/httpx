import pytest

import httpx


def test_request_repr():
    request = httpx.Request("GET", "http://example.org")
    assert repr(request) == "<Request('GET', 'http://example.org')>"


def test_no_content():
    request = httpx.Request("GET", "http://example.org")
    assert "Content-Length" not in request.headers


def test_content_length_header():
    request = httpx.Request("POST", "http://example.org", data=b"test 123")
    assert request.headers["Content-Length"] == "8"


def test_url_encoded_data():
    for RequestClass in (httpx.Request, httpx.AsyncRequest):
        request = RequestClass("POST", "http://example.org", data={"test": "123"})
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert request.content == b"test=123"


def test_json_encoded_data():
    for RequestClass in (httpx.Request, httpx.AsyncRequest):
        request = RequestClass("POST", "http://example.org", json={"test": 123})
        assert request.headers["Content-Type"] == "application/json"
        assert request.content == b'{"test": 123}'


def test_transfer_encoding_header():
    def streaming_body(data):
        yield data  # pragma: nocover

    data = streaming_body(b"test 123")

    request = httpx.Request("POST", "http://example.org", data=data)
    assert "Content-Length" not in request.headers
    assert request.headers["Transfer-Encoding"] == "chunked"


def test_override_host_header():
    headers = {"host": "1.2.3.4:80"}

    request = httpx.Request("GET", "http://example.org", headers=headers)
    assert request.headers["Host"] == "1.2.3.4:80"


def test_override_accept_encoding_header():
    headers = {"Accept-Encoding": "identity"}

    request = httpx.Request("GET", "http://example.org", headers=headers)
    assert request.headers["Accept-Encoding"] == "identity"


def test_override_content_length_header():
    def streaming_body(data):
        yield data  # pragma: nocover

    data = streaming_body(b"test 123")
    headers = {"Content-Length": "8"}

    request = httpx.Request("POST", "http://example.org", data=data, headers=headers)
    assert request.headers["Content-Length"] == "8"


def test_url():
    url = "http://example.org"
    request = httpx.Request("GET", url)
    assert request.url.scheme == "http"
    assert request.url.port == 80
    assert request.url.full_path == "/"

    url = "https://example.org/abc?foo=bar"
    request = httpx.Request("GET", url)
    assert request.url.scheme == "https"
    assert request.url.port == 443
    assert request.url.full_path == "/abc?foo=bar"


def test_invalid_urls():
    with pytest.raises(httpx.InvalidURL):
        httpx.Request("GET", "example.org")

    with pytest.raises(httpx.InvalidURL):
        httpx.Request("GET", "http:///foo")
