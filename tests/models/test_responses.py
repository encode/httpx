import datetime
import json
from unittest import mock

import brotli
import pytest

import httpx
from httpx._content_streams import AsyncIteratorStream, IteratorStream

REQUEST = httpx.Request("GET", "https://example.org")


def streaming_body():
    yield b"Hello, "
    yield b"world!"


async def async_streaming_body():
    yield b"Hello, "
    yield b"world!"


def test_response():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.request is REQUEST
    assert response.elapsed >= datetime.timedelta(0)
    assert not response.is_error


def test_raise_for_status():
    # 2xx status codes are not an error.
    response = httpx.Response(200, request=REQUEST)
    response.raise_for_status()

    # 4xx status codes are a client error.
    response = httpx.Response(403, request=REQUEST)
    with pytest.raises(httpx.HTTPStatusError):
        response.raise_for_status()

    # 5xx status codes are a server error.
    response = httpx.Response(500, request=REQUEST)
    with pytest.raises(httpx.HTTPStatusError):
        response.raise_for_status()

    # Calling .raise_for_status without setting a request instance is
    # not valid. Should raise a runtime error.
    response = httpx.Response(200)
    with pytest.raises(RuntimeError):
        response.raise_for_status()

def test_response_repr():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)
    assert repr(response) == "<Response [200 OK]>"


def test_response_content_type_encoding():
    """
    Use the charset encoding in the Content-Type header if possible.
    """
    headers = {"Content-Type": "text-plain; charset=latin-1"}
    content = "Latin 1: ÿ".encode("latin-1")
    response = httpx.Response(200, content=content, headers=headers, request=REQUEST)
    assert response.text == "Latin 1: ÿ"
    assert response.encoding == "latin-1"


def test_response_autodetect_encoding():
    """
    Autodetect encoding if there is no charset info in a Content-Type header.
    """
    content = "おはようございます。".encode("EUC-JP")
    response = httpx.Response(200, content=content, request=REQUEST)
    assert response.text == "おはようございます。"
    assert response.encoding == "EUC-JP"


def test_response_fallback_to_autodetect():
    """
    Fallback to autodetection if we get an invalid charset in the Content-Type header.
    """
    headers = {"Content-Type": "text-plain; charset=invalid-codec-name"}
    content = "おはようございます。".encode("EUC-JP")
    response = httpx.Response(200, content=content, headers=headers, request=REQUEST)
    assert response.text == "おはようございます。"
    assert response.encoding == "EUC-JP"


def test_response_default_text_encoding():
    """
    A media type of 'text/*' with no charset should default to ISO-8859-1.
    See: https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
    """
    content = b"Hello, world!"
    headers = {"Content-Type": "text/plain"}
    response = httpx.Response(200, content=content, headers=headers, request=REQUEST)
    assert response.status_code == 200
    assert response.encoding == "iso-8859-1"
    assert response.text == "Hello, world!"


def test_response_default_encoding():
    """
    Default to utf-8 if all else fails.
    """
    response = httpx.Response(200, content=b"", request=REQUEST)
    assert response.text == ""
    assert response.encoding == "utf-8"


def test_response_non_text_encoding():
    """
    Default to apparent encoding for non-text content-type headers.
    """
    headers = {"Content-Type": "image/png"}
    response = httpx.Response(200, content=b"xyz", headers=headers, request=REQUEST)
    assert response.text == "xyz"
    assert response.encoding == "ascii"


def test_response_set_explicit_encoding():
    headers = {
        "Content-Type": "text-plain; charset=utf-8"
    }  # Deliberately incorrect charset
    response = httpx.Response(
        200, content="Latin 1: ÿ".encode("latin-1"), headers=headers, request=REQUEST
    )
    response.encoding = "latin-1"
    assert response.text == "Latin 1: ÿ"
    assert response.encoding == "latin-1"


def test_response_force_encoding():
    response = httpx.Response(
        200, content="Snowman: ☃".encode("utf-8"), request=REQUEST
    )
    response.encoding = "iso-8859-1"
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Snowman: â\x98\x83"
    assert response.encoding == "iso-8859-1"


def test_read():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.encoding == "ascii"
    assert response.is_closed

    content = response.read()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_aread():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.encoding == "ascii"
    assert response.is_closed

    content = await response.aread()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


def test_iter_raw():
    stream = IteratorStream(iterator=streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    raw = b""
    for part in response.iter_raw():
        raw += part
    assert raw == b"Hello, world!"


@pytest.mark.asyncio
async def test_aiter_raw():
    stream = AsyncIteratorStream(aiterator=async_streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    raw = b""
    async for part in response.aiter_raw():
        raw += part
    assert raw == b"Hello, world!"


def test_iter_bytes():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    content = b""
    for part in response.iter_bytes():
        content += part
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_aiter_bytes():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    content = b""
    async for part in response.aiter_bytes():
        content += part
    assert content == b"Hello, world!"


def test_iter_text():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    content = ""
    for part in response.iter_text():
        content += part
    assert content == "Hello, world!"


@pytest.mark.asyncio
async def test_aiter_text():
    response = httpx.Response(200, content=b"Hello, world!", request=REQUEST)

    content = ""
    async for part in response.aiter_text():
        content += part
    assert content == "Hello, world!"


def test_iter_lines():
    response = httpx.Response(200, content=b"Hello,\nworld!", request=REQUEST)

    content = []
    for line in response.iter_lines():
        content.append(line)
    assert content == ["Hello,\n", "world!"]


@pytest.mark.asyncio
async def test_aiter_lines():
    response = httpx.Response(200, content=b"Hello,\nworld!", request=REQUEST)

    content = []
    async for line in response.aiter_lines():
        content.append(line)
    assert content == ["Hello,\n", "world!"]


def test_sync_streaming_response():
    stream = IteratorStream(iterator=streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    assert response.status_code == 200
    assert not response.is_closed

    content = response.read()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_async_streaming_response():
    stream = AsyncIteratorStream(aiterator=async_streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    assert response.status_code == 200
    assert not response.is_closed

    content = await response.aread()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


def test_cannot_read_after_stream_consumed():
    stream = IteratorStream(iterator=streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    content = b""
    for part in response.iter_bytes():
        content += part

    with pytest.raises(httpx.StreamConsumed):
        response.read()


@pytest.mark.asyncio
async def test_cannot_aread_after_stream_consumed():
    stream = AsyncIteratorStream(aiterator=async_streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    content = b""
    async for part in response.aiter_bytes():
        content += part

    with pytest.raises(httpx.StreamConsumed):
        await response.aread()


def test_cannot_read_after_response_closed():
    is_closed = False

    def close_func():
        nonlocal is_closed
        is_closed = True

    stream = IteratorStream(iterator=streaming_body(), close_func=close_func)
    response = httpx.Response(200, stream=stream, request=REQUEST)

    response.close()
    assert is_closed

    with pytest.raises(httpx.ResponseClosed):
        response.read()


@pytest.mark.asyncio
async def test_cannot_aread_after_response_closed():
    is_closed = False

    async def close_func():
        nonlocal is_closed
        is_closed = True

    stream = AsyncIteratorStream(
        aiterator=async_streaming_body(), close_func=close_func
    )
    response = httpx.Response(200, stream=stream, request=REQUEST)

    await response.aclose()
    assert is_closed

    with pytest.raises(httpx.ResponseClosed):
        await response.aread()


@pytest.mark.asyncio
async def test_elapsed_not_available_until_closed():
    stream = AsyncIteratorStream(aiterator=async_streaming_body())
    response = httpx.Response(200, stream=stream, request=REQUEST)

    with pytest.raises(RuntimeError):
        response.elapsed


def test_unknown_status_code():
    response = httpx.Response(600, request=REQUEST)
    assert response.status_code == 600
    assert response.reason_phrase == ""
    assert response.text == ""


def test_json_with_specified_encoding():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-16")
    headers = {"Content-Type": "application/json, charset=utf-16"}
    response = httpx.Response(200, content=content, headers=headers, request=REQUEST)
    assert response.json() == data


def test_json_with_options():
    data = {"greeting": "hello", "recipient": "world", "amount": 1}
    content = json.dumps(data).encode("utf-16")
    headers = {"Content-Type": "application/json, charset=utf-16"}
    response = httpx.Response(200, content=content, headers=headers, request=REQUEST)
    assert response.json(parse_int=str)["amount"] == "1"


def test_json_without_specified_encoding():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-32-be")
    headers = {"Content-Type": "application/json"}
    response = httpx.Response(200, content=content, headers=headers, request=REQUEST)
    assert response.json() == data


def test_json_without_specified_encoding_decode_error():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-32-be")
    headers = {"Content-Type": "application/json"}
    # force incorrect guess from `guess_json_utf` to trigger error
    with mock.patch("httpx._models.guess_json_utf", return_value="utf-32"):
        response = httpx.Response(
            200, content=content, headers=headers, request=REQUEST
        )
        with pytest.raises(json.decoder.JSONDecodeError):
            response.json()


def test_json_without_specified_encoding_value_error():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-32-be")
    headers = {"Content-Type": "application/json"}
    # force incorrect guess from `guess_json_utf` to trigger error
    with mock.patch("httpx._models.guess_json_utf", return_value="utf-32"):
        response = httpx.Response(200, content=content, headers=headers)
        with pytest.raises(ValueError):
            response.json()


@pytest.mark.parametrize(
    "headers, expected",
    [
        (
            {"Link": "<https://example.com>; rel='preload'"},
            {"preload": {"rel": "preload", "url": "https://example.com"}},
        ),
        (
            {"Link": '</hub>; rel="hub", </resource>; rel="self"'},
            {
                "hub": {"url": "/hub", "rel": "hub"},
                "self": {"url": "/resource", "rel": "self"},
            },
        ),
    ],
)
def test_link_headers(headers, expected):
    response = httpx.Response(200, content=None, headers=headers, request=REQUEST)
    assert response.links == expected


@pytest.mark.parametrize("header_value", (b"deflate", b"gzip", b"br"))
def test_decode_error_with_request(header_value):
    headers = [(b"Content-Encoding", header_value)]
    body = b"test 123"
    compressed_body = brotli.compress(body)[3:]
    with pytest.raises(httpx.DecodingError):
        httpx.Response(200, headers=headers, content=compressed_body, request=REQUEST)


@pytest.mark.parametrize("header_value", (b"deflate", b"gzip", b"br"))
def test_value_error_without_request(header_value):
    headers = [(b"Content-Encoding", header_value)]
    body = b"test 123"
    compressed_body = brotli.compress(body)[3:]
    with pytest.raises(ValueError):
        httpx.Response(200, headers=headers, content=compressed_body)


def test_response_with_unset_request():
    response = httpx.Response(200, content=b"Hello, world!")

    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert not response.is_error


def test_set_request_after_init():
    response = httpx.Response(200, content=b"Hello, world!")

    response.request = REQUEST

    assert response.request == REQUEST


def test_cannot_access_unset_request():
    response = httpx.Response(200, content=b"Hello, world!")

    with pytest.raises(RuntimeError):
        assert response.request is not None
