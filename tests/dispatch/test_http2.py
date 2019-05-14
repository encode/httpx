import json

import pytest

from httpcore import Client, Response
from .utils import MockHTTP2Backend


def app(request):
    content = json.dumps({
        "method": request.method,
        "path": request.url.path,
        "body": request.content.decode(),
    }).encode()
    headers = {'Content-Length': str(len(content))}
    return Response(200, headers=headers, content=content)


def test_http2_get_request():
    backend = MockHTTP2Backend(app=app)

    with Client(backend=backend) as client:
        response = client.get("http://example.org")

    assert response.status_code == 200
    assert json.loads(response.content) == {"method": "GET", "path": "/", "body": ""}


def test_http2_post_request():
    backend = MockHTTP2Backend(app=app)

    with Client(backend=backend) as client:
        response = client.post("http://example.org", data=b"<data>")

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": "<data>",
    }


def test_http2_multiple_requests():
    backend = MockHTTP2Backend(app=app)

    with Client(backend=backend) as client:
        response_1 = client.get("http://example.org/1")
        response_2 = client.get("http://example.org/2")
        response_3 = client.get("http://example.org/3")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}

    assert response_3.status_code == 200
    assert json.loads(response_3.content) == {"method": "GET", "path": "/3", "body": ""}
