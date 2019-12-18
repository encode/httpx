import datetime
import json
from unittest import mock

import pytest

import httpx


def streaming_body():
    yield b"Hello, "
    yield b"world!"


async def async_streaming_body():
    yield b"Hello, "
    yield b"world!"


def test_response():
    response = httpx.Response(200, content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.elapsed == datetime.timedelta(0)
    assert not response.is_error


def test_response_repr():
    response = httpx.Response(200, content=b"Hello, world!")
    assert repr(response) == "<Response [200 OK]>"


def test_response_content_type_encoding():
    """
    Use the charset encoding in the Content-Type header if possible.
    """
    headers = {"Content-Type": "text-plain; charset=latin-1"}
    content = "Latin 1: ÿ".encode("latin-1")
    response = httpx.Response(200, content=content, headers=headers)
    assert response.text == "Latin 1: ÿ"
    assert response.encoding == "latin-1"


def test_response_autodetect_encoding():
    """
    Autodetect encoding if there is no charset info in a Content-Type header.
    """
    content = "おはようございます。".encode("EUC-JP")
    response = httpx.Response(200, content=content)
    assert response.text == "おはようございます。"
    assert response.encoding == "EUC-JP"


def test_response_fallback_to_autodetect():
    """
    Fallback to autodetection if we get an invalid charset in the Content-Type header.
    """
    headers = {"Content-Type": "text-plain; charset=invalid-codec-name"}
    content = "おはようございます。".encode("EUC-JP")
    response = httpx.Response(200, content=content, headers=headers)
    assert response.text == "おはようございます。"
    assert response.encoding == "EUC-JP"


def test_response_default_text_encoding():
    """
    A media type of 'text/*' with no charset should default to ISO-8859-1.
    See: https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
    """
    content = b"Hello, world!"
    headers = {"Content-Type": "text/plain"}
    response = httpx.Response(200, content=content, headers=headers)
    assert response.status_code == 200
    assert response.encoding == "iso-8859-1"
    assert response.text == "Hello, world!"


def test_response_default_encoding():
    """
    Default to utf-8 if all else fails.
    """
    response = httpx.Response(200, content=b"")
    assert response.text == ""
    assert response.encoding == "utf-8"


def test_response_non_text_encoding():
    """
    Default to apparent encoding for non-text content-type headers.
    """
    headers = {"Content-Type": "image/png"}
    response = httpx.Response(200, content=b"xyz", headers=headers)
    assert response.text == "xyz"
    assert response.encoding == "ascii"


def test_response_set_explicit_encoding():
    headers = {
        "Content-Type": "text-plain; charset=utf-8"
    }  # Deliberately incorrect charset
    response = httpx.Response(
        200, content="Latin 1: ÿ".encode("latin-1"), headers=headers
    )
    response.encoding = "latin-1"
    assert response.text == "Latin 1: ÿ"
    assert response.encoding == "latin-1"


def test_response_force_encoding():
    response = httpx.Response(200, content="Snowman: ☃".encode("utf-8"))
    response.encoding = "iso-8859-1"
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Snowman: â\x98\x83"
    assert response.encoding == "iso-8859-1"


@pytest.mark.asyncio
async def test_read_response():
    response = httpx.Response(200, content=b"Hello, world!")

    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.encoding == "ascii"
    assert response.is_closed

    content = await response.aread()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_raw_interface():
    response = httpx.Response(200, content=b"Hello, world!")

    raw = b""
    async for part in response.aiter_raw():
        raw += part
    assert raw == b"Hello, world!"


@pytest.mark.asyncio
async def test_bytes_interface():
    response = httpx.Response(200, content=b"Hello, world!")

    content = b""
    async for part in response.aiter_bytes():
        content += part
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_text_interface():
    response = httpx.Response(200, content=b"Hello, world!")

    await response.aread()

    content = ""
    async for part in response.aiter_text():
        content += part
    assert content == "Hello, world!"


@pytest.mark.asyncio
async def test_lines_interface():
    response = httpx.Response(200, content=b"Hello,\nworld!")

    await response.aread()

    content = []
    async for line in response.aiter_lines():
        content.append(line)
    assert content == ["Hello,\n", "world!"]


@pytest.mark.asyncio
async def test_stream_interface_after_read():
    response = httpx.Response(200, content=b"Hello, world!")

    await response.aread()

    content = b""
    async for part in response.aiter_bytes():
        content += part
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_streaming_response():
    response = httpx.Response(200, content=async_streaming_body())

    assert response.status_code == 200
    assert not response.is_closed

    content = await response.aread()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_cannot_read_after_stream_consumed():
    response = httpx.Response(200, content=async_streaming_body())

    content = b""
    async for part in response.aiter_bytes():
        content += part

    with pytest.raises(httpx.StreamConsumed):
        await response.aread()


@pytest.mark.asyncio
async def test_cannot_read_after_response_closed():
    response = httpx.Response(200, content=async_streaming_body())

    await response.aclose()

    with pytest.raises(httpx.ResponseClosed):
        await response.aread()


def test_unknown_status_code():
    response = httpx.Response(600)
    assert response.status_code == 600
    assert response.reason_phrase == ""
    assert response.text == ""


def test_json_with_specified_encoding():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-16")
    headers = {"Content-Type": "application/json, charset=utf-16"}
    response = httpx.Response(200, content=content, headers=headers)
    assert response.json() == data


def test_json_with_options():
    data = {"greeting": "hello", "recipient": "world", "amount": 1}
    content = json.dumps(data).encode("utf-16")
    headers = {"Content-Type": "application/json, charset=utf-16"}
    response = httpx.Response(200, content=content, headers=headers)
    assert response.json(parse_int=str)["amount"] == "1"


def test_json_without_specified_encoding():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-32-be")
    headers = {"Content-Type": "application/json"}
    response = httpx.Response(200, content=content, headers=headers)
    assert response.json() == data


def test_json_without_specified_encoding_decode_error():
    data = {"greeting": "hello", "recipient": "world"}
    content = json.dumps(data).encode("utf-32-be")
    headers = {"Content-Type": "application/json"}
    # force incorrect guess from `guess_json_utf` to trigger error
    with mock.patch("httpx.models.guess_json_utf", return_value="utf-32"):
        response = httpx.Response(200, content=content, headers=headers)
        with pytest.raises(json.JSONDecodeError):
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
    response = httpx.Response(200, content=None, headers=headers)
    assert response.links == expected
