import zlib

import brotli
import pytest

import httpx
from httpx.decoders import TextDecoder


def test_deflate():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed_body = compressor.compress(body) + compressor.flush()

    headers = [(b"Content-Encoding", b"deflate")]
    response = httpx.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_gzip():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    compressed_body = compressor.compress(body) + compressor.flush()

    headers = [(b"Content-Encoding", b"gzip")]
    response = httpx.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_brotli():
    body = b"test 123"
    compressed_body = brotli.compress(body)

    headers = [(b"Content-Encoding", b"br")]
    response = httpx.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_multi():
    body = b"test 123"

    deflate_compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed_body = deflate_compressor.compress(body) + deflate_compressor.flush()

    gzip_compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    compressed_body = (
        gzip_compressor.compress(compressed_body) + gzip_compressor.flush()
    )

    headers = [(b"Content-Encoding", b"deflate, gzip")]
    response = httpx.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_multi_with_identity():
    body = b"test 123"
    compressed_body = brotli.compress(body)

    headers = [(b"Content-Encoding", b"br, identity")]
    response = httpx.Response(200, headers=headers, content=compressed_body)
    assert response.content == body

    headers = [(b"Content-Encoding", b"identity, br")]
    response = httpx.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_streaming():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    def compress(body):
        yield compressor.compress(body)
        yield compressor.flush()

    headers = [(b"Content-Encoding", b"gzip")]
    response = httpx.Response(200, headers=headers, content=compress(body))
    assert not hasattr(response, "body")
    assert response.read() == body


@pytest.mark.parametrize("header_value", (b"deflate", b"gzip", b"br"))
def test_decoding_errors(header_value):
    headers = [(b"Content-Encoding", header_value)]
    body = b"test 123"
    compressed_body = brotli.compress(body)[3:]
    with pytest.raises(httpx.exceptions.DecodingError):
        response = httpx.Response(200, headers=headers, content=compressed_body)
        response.content


@pytest.mark.parametrize(
    ["data", "encoding"],
    [
        ((b"Hello,", b" world!"), "ascii"),
        ((b"\xe3\x83", b"\x88\xe3\x83\xa9", b"\xe3", b"\x83\x99\xe3\x83\xab"), "utf-8"),
        ((b"\x83g\x83\x89\x83x\x83\x8b",) * 64, "shift-jis"),
        ((b"\x83g\x83\x89\x83x\x83\x8b",) * 600, "shift-jis"),
        (
            (b"\xcb\xee\xf0\xe5\xec \xe8\xef\xf1\xf3\xec \xe4\xee\xeb\xee\xf0",) * 64,
            "MacCyrillic",
        ),
        (
            (b"\xa5\xa6\xa5\xa7\xa5\xd6\xa4\xce\xb9\xf1\xba\xdd\xb2\xbd",) * 512,
            "euc-jp",
        ),
    ],
)
def test_text_decoder(data, encoding):
    def iterator():
        nonlocal data
        for chunk in data:
            yield chunk

    response = httpx.Response(200, content=iterator())
    assert "".join(response.stream_text()) == (b"".join(data)).decode(encoding)


def test_text_decoder_known_encoding():
    def iterator():
        yield b"\x83g"
        yield b"\x83"
        yield b"\x89\x83x\x83\x8b"

    response = httpx.Response(
        200,
        headers=[(b"Content-Type", b"text/html; charset=shift-jis")],
        content=iterator(),
    )

    assert "".join(response.stream_text()) == "トラベル"


def test_text_decoder_empty_cases():
    decoder = TextDecoder()
    assert decoder.flush() == ""

    decoder = TextDecoder()
    assert decoder.decode(b"") == ""
    assert decoder.flush() == ""
