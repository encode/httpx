import pytest

import httpcore


def test_request_repr():
    request = httpcore.Request("GET", "http://example.org")
    assert repr(request) == "<Request('GET', 'http://example.org')>"


def test_host_header():
    request = httpcore.Request("GET", "http://example.org")
    request.prepare()
    assert request.headers == httpcore.Headers(
        [(b"host", b"example.org"), (b"accept-encoding", b"deflate, gzip, br")]
    )


def test_content_length_header():
    request = httpcore.Request("POST", "http://example.org", content=b"test 123")
    request.prepare()
    assert request.headers == httpcore.Headers(
        [
            (b"host", b"example.org"),
            (b"content-length", b"8"),
            (b"accept-encoding", b"deflate, gzip, br"),
        ]
    )


def test_transfer_encoding_header():
    async def streaming_body(data):
        yield data  # pragma: nocover

    content = streaming_body(b"test 123")

    request = httpcore.Request("POST", "http://example.org", content=content)
    request.prepare()
    assert request.headers == httpcore.Headers(
        [
            (b"host", b"example.org"),
            (b"transfer-encoding", b"chunked"),
            (b"accept-encoding", b"deflate, gzip, br"),
        ]
    )


def test_override_host_header():
    headers = [(b"host", b"1.2.3.4:80")]

    request = httpcore.Request("GET", "http://example.org", headers=headers)
    request.prepare()
    assert request.headers == httpcore.Headers(
        [(b"accept-encoding", b"deflate, gzip, br"), (b"host", b"1.2.3.4:80")]
    )


def test_override_accept_encoding_header():
    headers = [(b"accept-encoding", b"identity")]

    request = httpcore.Request("GET", "http://example.org", headers=headers)
    request.prepare()
    assert request.headers == httpcore.Headers(
        [(b"host", b"example.org"), (b"accept-encoding", b"identity")]
    )


def test_override_content_length_header():
    async def streaming_body(data):
        yield data  # pragma: nocover

    content = streaming_body(b"test 123")
    headers = [(b"content-length", b"8")]

    request = httpcore.Request(
        "POST", "http://example.org", content=content, headers=headers
    )
    request.prepare()
    assert request.headers == httpcore.Headers(
        [
            (b"host", b"example.org"),
            (b"accept-encoding", b"deflate, gzip, br"),
            (b"content-length", b"8"),
        ]
    )


def test_url():
    request = httpcore.Request("GET", "http://example.org")
    assert request.url.scheme == "http"
    assert request.url.port == 80
    assert request.url.full_path == "/"

    request = httpcore.Request("GET", "https://example.org/abc?foo=bar")
    assert request.url.scheme == "https"
    assert request.url.port == 443
    assert request.url.full_path == "/abc?foo=bar"


def test_invalid_urls():
    with pytest.raises(httpcore.InvalidURL):
        httpcore.Request("GET", "example.org")

    with pytest.raises(httpcore.InvalidURL):
        httpcore.Request("GET", "invalid://example.org")

    with pytest.raises(httpcore.InvalidURL):
        httpcore.Request("GET", "http:///foo")
