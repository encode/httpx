import cgi
import io
import os
import typing
from unittest import mock

import pytest

import httpx
from httpx._content import encode_request
from httpx._utils import format_form_param


def echo_request_content(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=request.content)


@pytest.mark.parametrize(("value,output"), (("abc", b"abc"), (b"abc", b"abc")))
def test_multipart(value, output):
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    # Test with a single-value 'data' argument, and a plain file 'files' argument.
    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert response.status_code == 200

    # We're using the cgi module to verify the behavior here, which is a
    # bit grungy, but sufficient just for our testing purposes.
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict: dict = {
        "boundary": boundary.encode("ascii"),
        "CONTENT-LENGTH": content_length,
    }
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)

    # Note that the expected return type for text fields
    # appears to differs from 3.6 to 3.7+
    assert multipart["text"] == [output.decode()] or multipart["text"] == [output]
    assert multipart["file"] == [b"<file content>"]


@pytest.mark.parametrize(("key"), (b"abc", 1, 2.3, None))
def test_multipart_invalid_key(key):
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    data = {key: "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        client.post(
            "http://127.0.0.1:8000/",
            data=data,
            files=files,
        )
    assert "Invalid type for name" in str(e.value)
    assert repr(key) in str(e.value)


@pytest.mark.parametrize(("value"), (1, 2.3, None, [None, "abc"], {None: "abc"}))
def test_multipart_invalid_value(value):
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert "Invalid type for value" in str(e.value)


def test_multipart_file_tuple():
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    # Test with a list of values 'data' argument,
    #     and a tuple style 'files' argument.
    data = {"text": ["abc"]}
    files = {"file": ("name.txt", io.BytesIO(b"<file content>"))}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert response.status_code == 200

    # We're using the cgi module to verify the behavior here, which is a
    # bit grungy, but sufficient just for our testing purposes.
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict: dict = {
        "boundary": boundary.encode("ascii"),
        "CONTENT-LENGTH": content_length,
    }
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)

    # Note that the expected return type for text fields
    # appears to differs from 3.6 to 3.7+
    assert multipart["text"] == ["abc"] or multipart["text"] == [b"abc"]
    assert multipart["file"] == [b"<file content>"]


def test_multipart_encode(tmp_path: typing.Any) -> None:
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
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data=data, files=files)
        assert isinstance(stream, typing.Iterable)

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
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


def test_multipart_encode_files_allows_filenames_as_none() -> None:
    files = {"file": (None, io.BytesIO(b"<file content>"))}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data={}, files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            '--{0}\r\nContent-Disposition: form-data; name="file"\r\n\r\n'
            "<file content>\r\n--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


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
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data={}, files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{file_name}"\r\nContent-Type: '
            f"{expected_content_type}\r\n\r\n<file content>\r\n--{boundary}--\r\n"
            "".encode("ascii")
        )
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


@pytest.mark.parametrize(
    "value, output",
    ((b"<bytes content>", "<bytes content>"), ("<string content>", "<string content>")),
)
def test_multipart_encode_files_allows_bytes_or_str_content(
    value: typing.Union[str, bytes], output: str
) -> None:
    files = {"file": ("test.txt", value, "text/plain")}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data={}, files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            '--{0}\r\nContent-Disposition: form-data; name="file"; '
            'filename="test.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n{1}\r\n"
            "--{0}--\r\n"
            "".format(boundary, output).encode("ascii")
        )
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


def test_multipart_encode_non_seekable_filelike() -> None:
    """
    Test that special readable but non-seekable filelike objects are supported,
    at the cost of reading them into memory at most once.
    """

    class IteratorIO(io.IOBase):
        def __init__(self, iterator: typing.Iterator[bytes]) -> None:
            self._iterator = iterator

        def read(self, *args: typing.Any) -> bytes:
            return b"".join(self._iterator)

    def data() -> typing.Iterator[bytes]:
        yield b"Hello"
        yield b"World"

    fileobj: typing.Any = IteratorIO(data())
    files = {"file": fileobj}
    headers, stream = encode_request(files=files, boundary=b"+++")
    assert isinstance(stream, typing.Iterable)

    content = (
        b"--+++\r\n"
        b'Content-Disposition: form-data; name="file"; filename="upload"\r\n'
        b"Content-Type: application/octet-stream\r\n"
        b"\r\n"
        b"HelloWorld\r\n"
        b"--+++--\r\n"
    )
    assert headers == {
        "Content-Type": "multipart/form-data; boundary=+++",
        "Content-Length": str(len(content)),
    }
    assert content == b"".join(stream)


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
