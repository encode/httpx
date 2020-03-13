import io

import pytest

from httpx import StreamConsumed
from httpx._content_streams import ContentStream, encode


@pytest.mark.asyncio
async def test_base_content():
    stream = ContentStream()
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {}
    assert sync_content == b""
    assert async_content == b""


@pytest.mark.asyncio
async def test_empty_content():
    stream = encode()
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {}
    assert sync_content == b""
    assert async_content == b""


@pytest.mark.asyncio
async def test_bytes_content():
    stream = encode(data=b"Hello, world!")
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {"Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"


@pytest.mark.asyncio
async def test_iterator_content():
    def hello_world():
        yield b"Hello, "
        yield b"world!"

    stream = encode(data=hello_world())
    content = b"".join([part for part in stream])

    assert not stream.can_replay()
    assert stream.get_headers() == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(RuntimeError):
        [part async for part in stream]

    with pytest.raises(StreamConsumed):
        [part for part in stream]


@pytest.mark.asyncio
async def test_aiterator_content():
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    stream = encode(data=hello_world())
    content = b"".join([part async for part in stream])

    assert not stream.can_replay()
    assert stream.get_headers() == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(RuntimeError):
        [part for part in stream]

    with pytest.raises(StreamConsumed):
        [part async for part in stream]


@pytest.mark.asyncio
async def test_json_content():
    stream = encode(json={"Hello": "world!"})
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "19",
        "Content-Type": "application/json",
    }
    assert sync_content == b'{"Hello": "world!"}'
    assert async_content == b'{"Hello": "world!"}'


@pytest.mark.asyncio
async def test_urlencoded_content():
    stream = encode(data={"Hello": "world!"})
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "14",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"Hello=world%21"
    assert async_content == b"Hello=world%21"


@pytest.mark.asyncio
async def test_multipart_files_content():
    files = {"file": io.BytesIO(b"<file content>")}
    stream = encode(files=files, boundary=b"+++")
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
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
    stream = encode(data=data, files=files, boundary=b"+++")
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
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
    stream = encode(data={}, files={})
    sync_content = b"".join([part for part in stream])
    async_content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b""
    assert async_content == b""


def test_invalid_argument():
    with pytest.raises(TypeError):
        encode(123)
