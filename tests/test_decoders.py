from unittest import mock
import zlib

import brotli
import pytest

import httpcore


def test_deflate():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed_body = compressor.compress(body) + compressor.flush()

    headers = [(b"Content-Encoding", b"deflate")]
    response = httpcore.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_gzip():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    compressed_body = compressor.compress(body) + compressor.flush()

    headers = [(b"Content-Encoding", b"gzip")]
    response = httpcore.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_brotli():
    body = b"test 123"
    compressed_body = brotli.compress(body)

    headers = [(b"Content-Encoding", b"br")]
    response = httpcore.Response(200, headers=headers, content=compressed_body)
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
    response = httpcore.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


def test_multi_with_identity():
    body = b"test 123"
    compressed_body = brotli.compress(body)

    headers = [(b"Content-Encoding", b"br, identity")]
    response = httpcore.Response(200, headers=headers, content=compressed_body)
    assert response.content == body

    headers = [(b"Content-Encoding", b"identity, br")]
    response = httpcore.Response(200, headers=headers, content=compressed_body)
    assert response.content == body


@pytest.mark.asyncio
async def test_streaming():
    body = b"test 123"
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    async def compress(body):
        yield compressor.compress(body)
        yield compressor.flush()

    headers = [(b"Content-Encoding", b"gzip")]
    response = httpcore.Response(200, headers=headers, content=compress(body))
    assert not hasattr(response, "body")
    assert await response.read() == body


@pytest.mark.parametrize("header_value", (b"deflate", b"gzip", b"br"))
def test_decoding_errors(header_value):
    headers = [(b"Content-Encoding", header_value)]
    body = b"test 123"
    compressed_body = brotli.compress(body)[3:]
    with pytest.raises(httpcore.exceptions.DecodingError):
        response = httpcore.Response(200, headers=headers, content=compressed_body)
        response.content


@pytest.mark.parametrize("header_value", (b"deflate", b"gzip"))
def test_zlib_flush_errors(header_value):
    body = b"test 123"
    headers = [(b"Content-Encoding", header_value)]
    mock_decompressor = mock.Mock()
    mock_decompressor.decompress.return_value = body
    mock_decompressor.flush.side_effect = zlib.error
    with mock.patch(
        "httpcore.decoders.zlib.decompressobj", return_value=mock_decompressor
    ):
        with pytest.raises(httpcore.exceptions.DecodingError):
            response = httpcore.Response(200, headers=headers, content=body)
            response.content


def test_brotli_flush_error():
    body = b"test 123"
    headers = [(b"Content-Encoding", b"br")]
    mock_decompressor = mock.Mock()
    mock_decompressor.decompress.return_value = body
    mock_decompressor.finish.side_effect = brotli.Error
    with mock.patch(
        "httpcore.decoders.brotli.Decompressor", return_value=mock_decompressor
    ):
        with pytest.raises(httpcore.exceptions.DecodingError):
            response = httpcore.Response(200, headers=headers, content=body)
            response.content
