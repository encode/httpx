import io
import typing

import pytest

import httpx
from httpx._content import encode_request, encode_response


@pytest.mark.asyncio
async def test_empty_content():
    headers, stream = encode_request()
    assert isinstance(stream, httpx.SyncByteStream)
    assert isinstance(stream, httpx.AsyncByteStream)

    sync_content = stream.read()
    async_content = await stream.aread()

    assert headers == {}
    assert sync_content == b""
    assert async_content == b""


@pytest.mark.asyncio
async def test_bytes_content():
    headers, stream = encode_request(content=b"Hello, world!")
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {"Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"

    # Support 'data' for compat with requests.
    with pytest.warns(DeprecationWarning):
        headers, stream = encode_request(data=b"Hello, world!")  # type: ignore
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {"Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"


@pytest.mark.asyncio
async def test_bytesio_content():
    headers, stream = encode_request(content=io.BytesIO(b"Hello, world!"))
    assert isinstance(stream, typing.Iterable)
    assert not isinstance(stream, typing.AsyncIterable)

    content = b"".join([part for part in stream])

    assert headers == {"Content-Length": "13"}
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_async_bytesio_content():
    class AsyncBytesIO:
        def __init__(self, content):
            self._idx = 0
            self._content = content

        async def aread(self, chunk_size: int):
            chunk = self._content[self._idx : self._idx + chunk_size]
            self._idx = self._idx + chunk_size
            return chunk

        async def __aiter__(self):
            yield self._content  # pragma: nocover

    headers, stream = encode_request(content=AsyncBytesIO(b"Hello, world!"))
    assert not isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    content = b"".join([part async for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_iterator_content():
    def hello_world():
        yield b"Hello, "
        yield b"world!"

    headers, stream = encode_request(content=hello_world())
    assert isinstance(stream, typing.Iterable)
    assert not isinstance(stream, typing.AsyncIterable)

    content = b"".join([part for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        [part for part in stream]

    # Support 'data' for compat with requests.
    with pytest.warns(DeprecationWarning):
        headers, stream = encode_request(data=hello_world())  # type: ignore
    assert isinstance(stream, typing.Iterable)
    assert not isinstance(stream, typing.AsyncIterable)

    content = b"".join([part for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_aiterator_content():
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    headers, stream = encode_request(content=hello_world())
    assert not isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    content = b"".join([part async for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        [part async for part in stream]

    # Support 'data' for compat with requests.
    with pytest.warns(DeprecationWarning):
        headers, stream = encode_request(data=hello_world())  # type: ignore
    assert not isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    content = b"".join([part async for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"


@pytest.mark.asyncio
async def test_json_content():
    headers, stream = encode_request(json={"Hello": "world!"})
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "19",
        "Content-Type": "application/json",
    }
    assert sync_content == b'{"Hello": "world!"}'
    assert async_content == b'{"Hello": "world!"}'


@pytest.mark.asyncio
async def test_urlencoded_content():
    headers, stream = encode_request(data={"Hello": "world!"})
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "14",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"Hello=world%21"
    assert async_content == b"Hello=world%21"


@pytest.mark.asyncio
async def test_urlencoded_boolean():
    headers, stream = encode_request(data={"example": True})
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "12",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"example=true"
    assert async_content == b"example=true"


@pytest.mark.asyncio
async def test_urlencoded_none():
    headers, stream = encode_request(data={"example": None})
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "8",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"example="
    assert async_content == b"example="


@pytest.mark.asyncio
async def test_urlencoded_list():
    headers, stream = encode_request(data={"example": ["a", 1, True]})
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "32",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"example=a&example=1&example=true"
    assert async_content == b"example=a&example=1&example=true"


@pytest.mark.asyncio
async def test_multipart_files_content():
    files = {"file": io.BytesIO(b"<file content>")}
    headers, stream = encode_request(files=files, boundary=b"+++")
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "138",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert sync_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )
    assert async_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )


@pytest.mark.asyncio
async def test_multipart_data_and_files_content():
    data = {"message": "Hello, world!"}
    files = {"file": io.BytesIO(b"<file content>")}
    headers, stream = encode_request(data=data, files=files, boundary=b"+++")
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "210",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert sync_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="message"\r\n',
            b"\r\n",
            b"Hello, world!\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )
    assert async_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="message"\r\n',
            b"\r\n",
            b"Hello, world!\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )


@pytest.mark.asyncio
async def test_empty_request():
    headers, stream = encode_request(data={}, files={})
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {}
    assert sync_content == b""
    assert async_content == b""


def test_invalid_argument():
    with pytest.raises(TypeError):
        encode_request(123)  # type: ignore


@pytest.mark.asyncio
async def test_multipart_multiple_files_single_input_content():
    files = [
        ("file", io.BytesIO(b"<file content 1>")),
        ("file", io.BytesIO(b"<file content 2>")),
    ]
    headers, stream = encode_request(files=files, boundary=b"+++")
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {
        "Content-Length": "271",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert sync_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 1>\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 2>\r\n",
            b"--+++--\r\n",
        ]
    )
    assert async_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 1>\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 2>\r\n",
            b"--+++--\r\n",
        ]
    )


@pytest.mark.asyncio
async def test_response_empty_content():
    headers, stream = encode_response()
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {}
    assert sync_content == b""
    assert async_content == b""


@pytest.mark.asyncio
async def test_response_bytes_content():
    headers, stream = encode_response(content=b"Hello, world!")
    assert isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert headers == {"Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"


@pytest.mark.asyncio
async def test_response_iterator_content():
    def hello_world():
        yield b"Hello, "
        yield b"world!"

    headers, stream = encode_response(content=hello_world())
    assert isinstance(stream, typing.Iterable)
    assert not isinstance(stream, typing.AsyncIterable)

    content = b"".join([part for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        [part for part in stream]


@pytest.mark.asyncio
async def test_response_aiterator_content():
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    headers, stream = encode_response(content=hello_world())
    assert not isinstance(stream, typing.Iterable)
    assert isinstance(stream, typing.AsyncIterable)

    content = b"".join([part async for part in stream])

    assert headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        [part async for part in stream]


def test_response_invalid_argument():
    with pytest.raises(TypeError):
        encode_response(123)  # type: ignore
