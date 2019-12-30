import io

import pytest

from httpx.content_streams import encode
from httpx.exceptions import StreamConsumed


@pytest.mark.asyncio
async def test_empty_content():
    stream = encode()
    content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {}
    assert content == b""


@pytest.mark.asyncio
async def test_bytes_content():
    stream = encode(data=b"Hello, world!")
    content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {"Content-Length": "13"}
    assert content == b"Hello, world!"


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


@pytest.mark.asyncio
async def test_aiterator_is_stream_consumed():
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    stream = encode(data=hello_world())
    b"".join([part async for part in stream])

    assert stream.is_stream_consumed

    with pytest.raises(StreamConsumed) as _:
        b"".join([part async for part in stream])


@pytest.mark.asyncio
async def test_json_content():
    stream = encode(json={"Hello": "world!"})
    content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "19",
        "Content-Type": "application/json",
    }
    assert content == b'{"Hello": "world!"}'


@pytest.mark.asyncio
async def test_urlencoded_content():
    stream = encode(data={"Hello": "world!"})
    content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "14",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert content == b"Hello=world%21"


@pytest.mark.asyncio
async def test_multipart_files_content():
    files = {"file": io.BytesIO(b"<file content>")}
    stream = encode(files=files, boundary=b"+++")
    content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "138",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert content == b"".join(
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
    content = b"".join([part async for part in stream])

    assert stream.can_replay()
    assert stream.get_headers() == {
        "Content-Length": "210",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert content == b"".join(
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
