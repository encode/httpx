import zlib

import brotli
import http3
import pytest


def test_deflate():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed_body = compressor.compress(body) + compressor.flush()

    headers = [(b"Content-Encoding", b"deflate")]
    response = http3.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_gzip():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    compressed_body = compressor.compress(body) + compressor.flush()

    headers = [(b"Content-Encoding", b"gzip")]
    response = http3.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_brotli():
    body = b"test 123"
    compressed_body = brotli.compress(body)

    headers = [(b"Content-Encoding", b"br")]
    response = http3.Response(200, headers=headers, content=compressed_body)
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
    response = http3.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_multi_with_identity():
    body = b"test 123"
    compressed_body = brotli.compress(body)

    headers = [(b"Content-Encoding", b"br, identity")]
    response = http3.Response(200, headers=headers, content=compressed_body)
    assert response.content == body

    headers = [(b"Content-Encoding", b"identity, br")]
    response = http3.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_streaming():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    def compress(body):
        yield compressor.compress(body)
        yield compressor.flush()

    headers = [(b"Content-Encoding", b"gzip")]
    response = http3.Response(200, headers=headers, content=compress(body))
    assert not hasattr(response, "body")
    assert response.read() == body


@pytest.mark.parametrize("header_value", (b"deflate", b"gzip", b"br"))
def test_decoding_errors(header_value):
    headers = [(b"Content-Encoding", header_value)]
    body = b"test 123"
    compressed_body = brotli.compress(body)[3:]
    with pytest.raises(http3.exceptions.DecodingError):
        response = http3.Response(200, headers=headers, content=compressed_body)
        response.content
