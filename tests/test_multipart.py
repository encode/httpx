import io
import os
import tempfile
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
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    boundary_bytes = boundary.encode("ascii")

    assert response.status_code == 200
    assert response.content == b"".join(
        [
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="text"\r\n',
            b"\r\n",
            b"abc\r\n",
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--" + boundary_bytes + b"--\r\n",
        ]
    )


@pytest.mark.parametrize(
    "header",
    [
        "multipart/form-data; boundary=+++; charset=utf-8",
        "multipart/form-data; charset=utf-8; boundary=+++",
        "multipart/form-data; boundary=+++",
        "multipart/form-data; boundary=+++ ;",
        'multipart/form-data; boundary="+++"; charset=utf-8',
        'multipart/form-data; charset=utf-8; boundary="+++"',
        'multipart/form-data; boundary="+++"',
        'multipart/form-data; boundary="+++" ;',
    ],
)
def test_multipart_explicit_boundary(header: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    files = {"file": io.BytesIO(b"<file content>")}
    headers = {"content-type": header}
    response = client.post("http://127.0.0.1:8000/", files=files, headers=headers)
    boundary_bytes = b"+++"

    assert response.status_code == 200
    assert response.request.headers["Content-Type"] == header
    assert response.content == b"".join(
        [
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--" + boundary_bytes + b"--\r\n",
        ]
    )


@pytest.mark.parametrize(
    "header",
    [
        "multipart/form-data; charset=utf-8",
        "multipart/form-data; charset=utf-8; ",
    ],
)
def test_multipart_header_without_boundary(header: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    files = {"file": io.BytesIO(b"<file content>")}
    headers = {"content-type": header}
    response = client.post("http://127.0.0.1:8000/", files=files, headers=headers)

    assert response.status_code == 200
    assert response.request.headers["Content-Type"] == header


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


@pytest.mark.parametrize(("value"), (object(), {"key": "value"}))
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
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    boundary_bytes = boundary.encode("ascii")

    assert response.status_code == 200
    assert response.content == b"".join(
        [
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="text"\r\n',
            b"\r\n",
            b"abc\r\n",
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="file"; filename="name.txt"\r\n',
            b"Content-Type: text/plain\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--" + boundary_bytes + b"--\r\n",
        ]
    )


@pytest.mark.parametrize("content_type", [None, "text/plain"])
def test_multipart_file_tuple_headers(content_type: typing.Optional[str]):
    file_name = "test.txt"
    expected_content_type = "text/plain"
    headers = {"Expires": "0"}

    files = {"file": (file_name, io.BytesIO(b"<file content>"), content_type, headers)}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data={}, files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{file_name}"\r\nExpires: 0\r\nContent-Type: '
            f"{expected_content_type}\r\n\r\n<file content>\r\n--{boundary}--\r\n"
            "".encode("ascii")
        )
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


def test_multipart_headers_include_content_type() -> None:
    """Content-Type from 4th tuple parameter (headers) should override the 3rd parameter (content_type)"""
    file_name = "test.txt"
    expected_content_type = "image/png"
    headers = {"Content-Type": "image/png"}

    files = {"file": (file_name, io.BytesIO(b"<file content>"), "text_plain", headers)}
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


def test_multipart_encode(tmp_path: typing.Any) -> None:
    path = str(tmp_path / "name.txt")
    with open(path, "wb") as f:
        f.write(b"<file content>")

    data = {
        "a": "1",
        "b": b"C",
        "c": ["11", "22", "33"],
        "d": "",
        "e": True,
        "f": "",
    }
    with open(path, "rb") as input_file:
        files = {"file": ("name.txt", input_file)}

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
                '--{0}\r\nContent-Disposition: form-data; name="e"\r\n\r\ntrue\r\n'
                '--{0}\r\nContent-Disposition: form-data; name="f"\r\n\r\n\r\n'
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


def test_multipart_encode_unicode_file_contents() -> None:
    files = {"file": ("name.txt", b"<bytes content>")}

    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            '--{0}\r\nContent-Disposition: form-data; name="file";'
            ' filename="name.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<bytes content>\r\n"
            "--{0}--\r\n"
            "".format(boundary).encode("utf-8")
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


def test_multipart_encode_files_allows_bytes_content() -> None:
    files = {"file": ("test.txt", b"<bytes content>", "text/plain")}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data={}, files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            '--{0}\r\nContent-Disposition: form-data; name="file"; '
            'filename="test.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<bytes content>\r\n"
            "--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


def test_multipart_encode_files_allows_str_content() -> None:
    files = {"file": ("test.txt", "<str content>", "text/plain")}
    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = os.urandom(16).hex()

        headers, stream = encode_request(data={}, files=files)
        assert isinstance(stream, typing.Iterable)

        content = (
            '--{0}\r\nContent-Disposition: form-data; name="file"; '
            'filename="test.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<str content>\r\n"
            "--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )
        assert headers == {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(content)),
        }
        assert content == b"".join(stream)


def test_multipart_encode_files_raises_exception_with_StringIO_content() -> None:
    files = {"file": ("test.txt", io.StringIO("content"), "text/plain")}
    with pytest.raises(TypeError):
        encode_request(data={}, files=files)  # type: ignore


def test_multipart_encode_files_raises_exception_with_text_mode_file() -> None:
    with tempfile.TemporaryFile(mode="w") as upload:
        files = {"file": ("test.txt", upload, "text/plain")}
        with pytest.raises(TypeError):
            encode_request(data={}, files=files)  # type: ignore


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


def test_multipart_rewinds_files():
    with tempfile.TemporaryFile() as upload:
        upload.write(b"Hello, world!")

        transport = httpx.MockTransport(echo_request_content)
        client = httpx.Client(transport=transport)

        files = {"file": upload}
        response = client.post("http://127.0.0.1:8000/", files=files)
        assert response.status_code == 200
        assert b"\r\nHello, world!\r\n" in response.content

        # POSTing the same file instance a second time should have the same content.
        files = {"file": upload}
        response = client.post("http://127.0.0.1:8000/", files=files)
        assert response.status_code == 200
        assert b"\r\nHello, world!\r\n" in response.content


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
