import cgi
import io

import pytest

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
    data = {"text": "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict = {"boundary": boundary.encode("ascii"), "CONTENT-LENGTH": content_length}
    assert response.status_code == 200
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)
    assert multipart["text"] == ["abc"]
    assert multipart["file"] == [b"<file content>"]


def test_multipart_file_tuple():
    client = Client(dispatch=MockDispatch())
    data = {"text": ["abc"]}
    files = {"file": ("name.txt", io.BytesIO(b"<file content>"))}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    content_length = response.request.headers["Content-Length"]
    pdict = {"boundary": boundary.encode("ascii"), "CONTENT-LENGTH": content_length}
    assert response.status_code == 200
    multipart = cgi.parse_multipart(io.BytesIO(response.content), pdict)
    assert multipart["text"] == ["abc"]
    assert multipart["file"] == [b"<file content>"]
