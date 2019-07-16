import cgi
import io

from http3 import (
    CertTypes,
    Client,
    Dispatcher,
    Request,
    Response,
    TimeoutTypes,
    VerifyTypes,
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


def test_multipart():
    client = Client(dispatch=MockDispatch())

    # Test with a single-value 'data' argument, and a plain file 'files' argument.
    data = {"text": "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert response.status_code == 200

    # We're using the cgi module to verify the behavior here, which is a
    # bit grungy, but sufficient just for our testing purposes.
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict = {"boundary": boundary.encode("ascii"), "CONTENT-LENGTH": content_length}
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)

    # Note that the expected return type for text
    # fields appears to differs from 3.6 to 3.7+
    assert multipart["text"] == ["abc"] or multipart["text"] == [b"abc"]
    assert multipart["file"] == [b"<file content>"]


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

    # Note that the expected return type for text fields appears
    # to differs from 3.6 to 3.7+
    assert multipart["text"] == ["abc"] or multipart["text"] == [b"abc"]
    assert multipart["file"] == [b"<file content>"]
