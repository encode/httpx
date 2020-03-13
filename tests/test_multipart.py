import binascii
import cgi
import io
import os
import typing
from typing import Any, List, cast
from unittest import mock

import httpcore
import memory_profiler
import pytest

import httpx
from httpx._content_streams import AsyncIteratorStream, MultipartStream, encode
from httpx._utils import format_form_param


class MockDispatch(httpcore.AsyncHTTPTransport):
    async def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, int, bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: typing.Dict[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes,
        int,
        bytes,
        typing.List[typing.Tuple[bytes, bytes]],
        httpcore.AsyncByteStream,
    ]:
        content = AsyncIteratorStream(aiterator=(part async for part in stream))
        return b"HTTP/1.1", 200, b"OK", [], content


@pytest.mark.parametrize(("value,output"), (("abc", b"abc"), (b"abc", b"abc")))
@pytest.mark.asyncio
async def test_multipart(value, output):
    client = httpx.AsyncClient(dispatch=MockDispatch())

    # Test with a single-value 'data' argument, and a plain file 'files' argument.
    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    response = await client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert response.status_code == 200

    # We're using the cgi module to verify the behavior here, which is a
    # bit grungy, but sufficient just for our testing purposes.
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict = {"boundary": boundary.encode("ascii"), "CONTENT-LENGTH": content_length}
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)

    # Note that the expected return type for text fields
    # appears to differs from 3.6 to 3.7+
    assert multipart["text"] == [output.decode()] or multipart["text"] == [output]
    assert multipart["file"] == [b"<file content>"]


@pytest.mark.parametrize(("key"), (b"abc", 1, 2.3, None))
@pytest.mark.asyncio
async def test_multipart_invalid_key(key):
    client = httpx.AsyncClient(dispatch=MockDispatch())
    data = {key: "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        await client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert "Invalid type for name" in str(e.value)


@pytest.mark.parametrize(("value"), (1, 2.3, None, [None, "abc"], {None: "abc"}))
@pytest.mark.asyncio
async def test_multipart_invalid_value(value):
    client = httpx.AsyncClient(dispatch=MockDispatch())
    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        await client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert "Invalid type for value" in str(e.value)


@pytest.mark.asyncio
async def test_multipart_file_tuple():
    client = httpx.AsyncClient(dispatch=MockDispatch())

    # Test with a list of values 'data' argument, and a tuple style 'files' argument.
    data = {"text": ["abc"]}
    files = {"file": ("name.txt", io.BytesIO(b"<file content>"))}
    response = await client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert response.status_code == 200

    # We're using the cgi module to verify the behavior here, which is a
    # bit grungy, but sufficient just for our testing purposes.
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict = {"boundary": boundary.encode("ascii"), "CONTENT-LENGTH": content_length}
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)

    # Note that the expected return type for text fields
    # appears to differs from 3.6 to 3.7+
    assert multipart["text"] == ["abc"] or multipart["text"] == [b"abc"]
    assert multipart["file"] == [b"<file content>"]


def test_multipart_encode(tmp_path: Any) -> None:
    path = str(tmp_path / "name.txt")
    with open(path, "wb") as f:
        f.write(b"<file content>")

    data = {
        "a": "1",
        "b": b"C",
        "c": ["11", "22", "33"],
        "d": "",
    }
    files = {"file": ("name.txt", open(path, "rb"))}

    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = binascii.hexlify(os.urandom(16)).decode("ascii")

        stream = cast(MultipartStream, encode(data=data, files=files))
        assert stream.can_replay()

        assert stream.content_type == f"multipart/form-data; boundary={boundary}"
        content = (
            '--{0}\r\nContent-Disposition: form-data; name="a"\r\n\r\n1\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="b"\r\n\r\nC\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="c"\r\n\r\n11\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="c"\r\n\r\n22\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="c"\r\n\r\n33\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="d"\r\n\r\n\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="file";'
            ' filename="name.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<file content>\r\n"
            "--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )
        assert stream.get_headers()["Content-Length"] == str(len(content))
        assert b"".join(stream) == content


def test_multipart_encode_files_allows_filenames_as_none() -> None:
    files = {"file": (None, io.BytesIO(b"<file content>"))}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = binascii.hexlify(os.urandom(16)).decode("ascii")

        stream = cast(MultipartStream, encode(data={}, files=files))
        assert stream.can_replay()

        assert stream.content_type == f"multipart/form-data; boundary={boundary}"
        assert b"".join(stream) == (
            '--{0}\r\nContent-Disposition: form-data; name="file"\r\n\r\n'
            "<file content>\r\n--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )


@pytest.mark.parametrize(
    "file_name,expected_content_type",
    [
        ("example.json", "application/json"),
        ("example.txt", "text/plain"),
        ("no-extension", "application/octet-stream"),
    ],
)
def test_multipart_encode_files_guesses_correct_content_type(
    file_name: str, expected_content_type: str
) -> None:
    files = {"file": (file_name, io.BytesIO(b"<file content>"))}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = binascii.hexlify(os.urandom(16)).decode("ascii")

        stream = cast(MultipartStream, encode(data={}, files=files))
        assert stream.can_replay()

        assert stream.content_type == f"multipart/form-data; boundary={boundary}"
        assert b"".join(stream) == (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{file_name}"\r\nContent-Type: '
            f"{expected_content_type}\r\n\r\n<file content>\r\n--{boundary}--\r\n"
            "".encode("ascii")
        )


def test_multipart_encode_files_allows_str_content() -> None:
    files = {"file": ("test.txt", "<string content>", "text/plain")}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = binascii.hexlify(os.urandom(16)).decode("ascii")

        stream = cast(MultipartStream, encode(data={}, files=files))
        assert stream.can_replay()

        assert stream.content_type == f"multipart/form-data; boundary={boundary}"
        content = (
            '--{0}\r\nContent-Disposition: form-data; name="file"; '
            'filename="test.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<string content>\r\n"
            "--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )
        assert stream.get_headers()["Content-Length"] == str(len(content))
        assert b"".join(stream) == content


def test_multipart_file_streaming_memory(tmp_path: Any) -> None:
    """
    Test that multipart file uploads are effectively streaming, i.e. they don't
    result in loading the entire file into memory.
    """
    path = str(tmp_path / "name.txt")

    # Flush a relatively large file to disk to read from.
    ONE_MB = 1024 * 1024
    size_mb = 1
    with open(path, "wb") as out:
        out.write(os.urandom(int(size_mb * ONE_MB)))

    def bench() -> None:
        files = {"file": open(path, "rb")}
        stream = encode(files=files, boundary=b"+++")
        # Consume the stream one chunk at a time.
        for _ in stream:
            pass

    # Measure memory usage of `main()` -- one entry per LOC (plus init/teardown).
    memory_per_line: List[float] = memory_profiler.memory_usage((bench, (), {}))

    # Rationale: if streaming works correctly, all lines should use roughly the
    # same amount of memory. In particular, they should use the same amount of memory
    # than the first operation in `main()`.
    percents = 1
    baseline = memory_per_line[0]
    max_allowed_memory = (100 + percents) / 100 * baseline

    # Make sure initial file was big enough to exceed memory limits
    # if it were to be consumed in full.
    assert (
        size_mb > max_allowed_memory - baseline
    ), "Impact of loading entire file in memory wouldn't be detectable"

    # Now verify memory usage.
    assert all(memory < max_allowed_memory for memory in memory_per_line), (
        max_allowed_memory,
        memory_per_line,
    )


class TestHeaderParamHTML5Formatting:
    def test_unicode(self):
        param = format_form_param("filename", "n\u00e4me")
        assert param == b'filename="n\xc3\xa4me"'

    def test_ascii(self):
        param = format_form_param("filename", b"name")
        assert param == b'filename="name"'

    def test_unicode_escape(self):
        param = format_form_param("filename", "hello\\world\u0022")
        assert param == b'filename="hello\\\\world%22"'

    def test_unicode_with_control_character(self):
        param = format_form_param("filename", "hello\x1A\x1B\x1C")
        assert param == b'filename="hello%1A\x1B%1C"'
