import sys

import pytest

import http3


def hello_world(environ, start_response):
    status = "200 OK"
    output = b"Hello, World!"

    response_headers = [
        ("Content-type", "text/plain"),
        ("Content-Length", str(len(output))),
    ]

    start_response(status, response_headers)

    return [output]


def raise_exc(environ, start_response):
    status = "500 Server Error"
    output = b"Nope!"

    response_headers = [
        ("Content-type", "text/plain"),
        ("Content-Length", str(len(output))),
    ]

    try:
        raise ValueError()
    except:
        exc_info = sys.exc_info()
        start_response(status, response_headers, exc_info=exc_info)

    return [output]


def test_wsgi():
    client = http3.Client(app=hello_world)
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_wsgi_exc():
    client = http3.Client(app=raise_exc)
    with pytest.raises(ValueError):
        response = client.get("http://www.example.org/")
