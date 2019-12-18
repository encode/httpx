import io

import pytest

from httpx.content import encode


@pytest.mark.asyncio
async def test_empty_content():
    content = encode()

    assert content.can_replay()
    assert content.get_headers() == {}
    assert await content.aread() == b""


@pytest.mark.asyncio
async def test_bytes_content():
    content = encode(data=b"Hello, world!")

    assert content.can_replay()
    assert content.get_headers() == {"Content-Length": "13"}
    assert await content.aread() == b"Hello, world!"


@pytest.mark.asyncio
async def test_aiterator_content():
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    content = encode(data=hello_world())

    assert not content.can_replay()
    assert content.get_headers() == {"Transfer-Encoding": "chunked"}
    assert await content.aread() == b"Hello, world!"


@pytest.mark.asyncio
async def test_json_content():
    content = encode(json={"Hello": "world!"})

    assert content.can_replay()
    assert content.get_headers() == {
        "Content-Length": "19",
        "Content-Type": "application/json",
    }
    assert await content.aread() == b'{"Hello": "world!"}'


@pytest.mark.asyncio
async def test_urlencoded_content():
    content = encode(data={"Hello": "world!"})

    assert content.can_replay()
    assert content.get_headers() == {
        "Content-Length": "14",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert await content.aread() == b"Hello=world%21"


@pytest.mark.asyncio
async def test_multipart_files_content():
    files = {"file": io.BytesIO(b"<file content>")}
    content = encode(files=files, boundary=b"+++")

    assert content.can_replay()
    assert content.get_headers() == {
        "Content-Length": "138",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert await content.aread() == b"".join(
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
    content = encode(data=data, files=files, boundary=b"+++")

    assert content.can_replay()
    assert content.get_headers() == {
        "Content-Length": "210",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert await content.aread() == b"".join(
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
