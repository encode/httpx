import typing

import pytest

import httpx


def test_request_repr():
    request = httpx.Request("GET", "http://example.org")
    assert repr(request) == "<Request('GET', 'http://example.org')>"


def test_no_content():
    request = httpx.Request("GET", "http://example.org")
    assert "Content-Length" not in request.headers


def test_content_length_header():
    request = httpx.Request("POST", "http://example.org", content=b"test 123")
    assert request.headers["Content-Length"] == "8"


def test_iterable_content():
    class Content:
        def __iter__(self):
            yield b"test 123"  # pragma: nocover

    request = httpx.Request("POST", "http://example.org", content=Content())
    assert request.headers == httpx.Headers(
        {"Host": "example.org", "Transfer-Encoding": "chunked"}
    )


def test_generator_with_transfer_encoding_header():
    def content():
        yield b"test 123"  # pragma: nocover

    request = httpx.Request("POST", "http://example.org", content=content())
    assert request.headers == httpx.Headers(
        {"Host": "example.org", "Transfer-Encoding": "chunked"}
    )


def test_generator_with_content_length_header():
    def content():
        yield b"test 123"  # pragma: nocover

    headers = {"Content-Length": "8"}
    request = httpx.Request(
        "POST", "http://example.org", content=content(), headers=headers
    )
    assert request.headers == httpx.Headers(
        {"Host": "example.org", "Content-Length": "8"}
    )


def test_url_encoded_data():
    request = httpx.Request("POST", "http://example.org", data={"test": "123"})
    request.read()

    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.content == b"test=123"


def test_json_encoded_data():
    request = httpx.Request("POST", "http://example.org", json={"test": 123})
    request.read()

    assert request.headers["Content-Type"] == "application/json"
    assert request.content == b'{"test": 123}'


def test_headers():
    request = httpx.Request("POST", "http://example.org", json={"test": 123})

    assert request.headers == httpx.Headers(
        {
            "Host": "example.org",
            "Content-Type": "application/json",
            "Content-Length": "13",
        }
    )


def test_read_and_stream_data():
    # Ensure a request may still be streamed if it has been read.
    # Needed for cases such as authentication classes that read the request body.
    request = httpx.Request("POST", "http://example.org", json={"test": 123})
    request.read()
    assert request.stream is not None
    assert isinstance(request.stream, typing.Iterable)
    content = b"".join([part for part in request.stream])
    assert content == request.content


@pytest.mark.asyncio
async def test_aread_and_stream_data():
    # Ensure a request may still be streamed if it has been read.
    # Needed for cases such as authentication classes that read the request body.
    request = httpx.Request("POST", "http://example.org", json={"test": 123})
    await request.aread()
    assert request.stream is not None
    assert isinstance(request.stream, typing.AsyncIterable)
    content = b"".join([part async for part in request.stream])
    assert content == request.content


@pytest.mark.asyncio
async def test_cannot_access_content_without_read():
    # Ensure a request may still be streamed if it has been read.
    # Needed for cases such as authentication classes that read the request body.
    request = httpx.Request("POST", "http://example.org", json={"test": 123})
    with pytest.raises(httpx.RequestNotRead):
        request.content


def test_transfer_encoding_header():
    async def streaming_body(data):
        yield data  # pragma: nocover

    data = streaming_body(b"test 123")

    request = httpx.Request("POST", "http://example.org", data=data)
    assert "Content-Length" not in request.headers
    assert request.headers["Transfer-Encoding"] == "chunked"


def test_ignore_transfer_encoding_header_if_content_length_exists():
    """
    `Transfer-Encoding` should be ignored if `Content-Length` has been set explicitly.
    See https://github.com/encode/httpx/issues/1168
    """

    def streaming_body(data):
        yield data  # pragma: nocover

    data = streaming_body(b"abcd")

    headers = {"Content-Length": "4"}
    request = httpx.Request("POST", "http://example.org", data=data, headers=headers)
    assert "Transfer-Encoding" not in request.headers
    assert request.headers["Content-Length"] == "4"


def test_override_host_header():
    headers = {"host": "1.2.3.4:80"}

    request = httpx.Request("GET", "http://example.org", headers=headers)
    assert request.headers["Host"] == "1.2.3.4:80"


def test_override_accept_encoding_header():
    headers = {"Accept-Encoding": "identity"}

    request = httpx.Request("GET", "http://example.org", headers=headers)
    assert request.headers["Accept-Encoding"] == "identity"


def test_override_content_length_header():
    async def streaming_body(data):
        yield data  # pragma: nocover

    data = streaming_body(b"test 123")
    headers = {"Content-Length": "8"}

    request = httpx.Request("POST", "http://example.org", data=data, headers=headers)
    assert request.headers["Content-Length"] == "8"


def test_url():
    url = "http://example.org"
    request = httpx.Request("GET", url)
    assert request.url.scheme == "http"
    assert request.url.port is None
    assert request.url.full_path == "/"

    url = "https://example.org/abc?foo=bar"
    request = httpx.Request("GET", url)
    assert request.url.scheme == "https"
    assert request.url.port is None
    assert request.url.full_path == "/abc?foo=bar"
