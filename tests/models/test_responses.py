import pytest

import httpcore


async def streaming_body():
    yield b"Hello, "
    yield b"world!"


def test_response():
    response = httpcore.Response(200, content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"


def test_response_content_type_encoding():
    """
    Use the charset encoding in the Content-Type header if possible.
    """
    headers = {"Content-Type": "text-plain; charset=latin-1"}
    content = "Latin 1: ÿ".encode("latin-1")
    response = httpcore.Response(200, content=content, headers=headers)
    assert response.text == "Latin 1: ÿ"
    assert response.encoding == "latin-1"


def test_response_autodetect_encoding():
    """
    Autodetect encoding if there is no charset info in a Content-Type header.
    """
    content = "おはようございます。".encode("EUC-JP")
    response = httpcore.Response(200, content=content)
    assert response.text == "おはようございます。"
    assert response.encoding == "EUC-JP"


def test_response_fallback_to_autodetect():
    """
    Fallback to autodetection if we get an invalid charset in the Content-Type header.
    """
    headers = {"Content-Type": "text-plain; charset=invalid-codec-name"}
    content = "おはようございます。".encode("EUC-JP")
    response = httpcore.Response(200, content=content, headers=headers)
    assert response.text == "おはようございます。"
    assert response.encoding == "EUC-JP"


def test_response():
    """
    A media type of 'text/*' with no charset should default to ISO-8859-1.
    See: https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
    """
    content = b"Hello, world!"
    headers = {"Content-Type": "text/plain"}
    response = httpcore.Response(200, content=content, headers=headers)
    assert response.status_code == 200
    assert response.encoding == "iso-8859-1"
    assert response.text == "Hello, world!"


def test_response_default_encoding():
    """
    Default to utf-8 if all else fails.
    """
    response = httpcore.Response(200, content=b"")
    assert response.text == ""
    assert response.encoding == "utf-8"


def test_response_set_explicit_encoding():
    headers = {
        "Content-Type": "text-plain; charset=utf-8"
    }  # Deliberately incorrect charset
    response = httpcore.Response(
        200, content="Latin 1: ÿ".encode("latin-1"), headers=headers
    )
    response.encoding = "latin-1"
    assert response.text == "Latin 1: ÿ"
    assert response.encoding == "latin-1"


def test_response_force_encoding():
    response = httpcore.Response(200, content="Snowman: ☃".encode("utf-8"))
    response.encoding = "iso-8859-1"
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Snowman: â\x98\x83"
    assert response.encoding == "iso-8859-1"


@pytest.mark.asyncio
async def test_read_response():
    response = httpcore.Response(200, content=b"Hello, world!")

    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.encoding == "ascii"
    assert response.is_closed

    content = await response.read()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_raw_interface():
    response = httpcore.Response(200, content=b"Hello, world!")

    raw = b""
    async for part in response.raw():
        raw += part
    assert raw == b"Hello, world!"


@pytest.mark.asyncio
async def test_stream_interface():
    response = httpcore.Response(200, content=b"Hello, world!")

    content = b""
    async for part in response.stream():
        content += part
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_stream_interface_after_read():
    response = httpcore.Response(200, content=b"Hello, world!")

    await response.read()

    content = b""
    async for part in response.stream():
        content += part
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_streaming_response():
    response = httpcore.Response(200, content=streaming_body())

    assert response.status_code == 200
    assert not response.is_closed

    content = await response.read()

    assert content == b"Hello, world!"
    assert response.content == b"Hello, world!"
    assert response.is_closed


@pytest.mark.asyncio
async def test_cannot_read_after_stream_consumed():
    response = httpcore.Response(200, content=streaming_body())

    content = b""
    async for part in response.stream():
        content += part

    with pytest.raises(httpcore.StreamConsumed):
        await response.read()


@pytest.mark.asyncio
async def test_cannot_read_after_response_closed():
    response = httpcore.Response(200, content=streaming_body())

    await response.close()

    with pytest.raises(httpcore.ResponseClosed):
        await response.read()


def test_unknown_status_code():
    response = httpcore.Response(600)
    assert response.status_code == 600
    assert response.reason_phrase == ""
    assert response.text == ""
