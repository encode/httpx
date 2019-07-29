import binascii
import cgi
import io
import os
from unittest import mock

import pytest

from httpx import (
    CertTypes,
    Client,
    Dispatcher,
    Request,
    Response,
    TimeoutTypes,
    VerifyTypes,
    multipart,
)


class MockDispatch(Dispatcher):
    def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        return Response(200, content=request.read())


@pytest.mark.parametrize(("value,output"), (("abc", b"abc"), (b"abc", b"abc")))
def test_multipart(value, output):
    client = Client(dispatch=MockDispatch())

    # Test with a single-value 'data' argument, and a plain file 'files' argument.
    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
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
def test_multipart_invalid_key(key):
    client = Client(dispatch=MockDispatch())
    data = {key: "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert "Invalid type for name" in str(e.value)


@pytest.mark.parametrize(("value"), (1, 2.3, None, [None, "abc"], {None: "abc"}))
def test_multipart_invalid_value(value):
    client = Client(dispatch=MockDispatch())
    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert "Invalid type for value" in str(e.value)


def test_multipart_file_tuple():
    client = Client(dispatch=MockDispatch())

    # Test with a list of values 'data' argument, and a tuple style 'files' argument.
    data = {"text": ["abc"]}
    files = {"file": ("name.txt", io.BytesIO(b"<file content>"))}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
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


def test_multipart_encode():
    data = {
        "a": "1",
        "b": b"C",
        "c": ["11", "22", "33"],
        "d": {"ff": ["1", b"2", "3"], "fff": ["11", b"22", "33"]},
        "f": "",
    }
    files = {"file": ("name.txt", io.BytesIO(b"<file content>"))}

    with mock.patch("os.urandom", return_value=os.urandom(16)):
        boundary = binascii.hexlify(os.urandom(16)).decode("ascii")
        body, content_type = multipart.multipart_encode(data=data, files=files)
        assert content_type == f"multipart/form-data; boundary={boundary}"
        assert body == (
            '--{0}\r\nContent-Disposition: form-data; name="a"\r\n\r\n1\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="b"\r\n\r\nC\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="c"\r\n\r\n11\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="c"\r\n\r\n22\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="c"\r\n\r\n33\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="d"\r\n\r\nff\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="d"\r\n\r\nfff\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="f"\r\n\r\n\r\n'
            '--{0}\r\nContent-Disposition: form-data; name="file";'
            ' filename="name.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<file content>\r\n"
            "--{0}--\r\n"
            "".format(boundary).encode("ascii")
        )


class TestHeaderParamHTML5Formatting:
    def test_unicode(self):
        param = multipart._format_param("filename", "n\u00e4me")
        assert param == 'filename="n\u00e4me"'

    def test_ascii(self):
        param = multipart._format_param("filename", b"name")
        assert param == 'filename="name"'

    def test_unicode_escape(self):
        param = multipart._format_param("filename", "hello\\world\u0022")
        assert param == 'filename="hello\\\\world%22"'

    def test_unicode_with_control_character(self):
        param = multipart._format_param("filename", "hello\x1A\x1B\x1C")
        assert param == 'filename="hello%1A\x1B%1C"'
