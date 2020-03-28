import sys

import pytest

import httpx


def application_factory(output):
    def application(environ, start_response):
        status = "200 OK"

        response_headers = [
            ("Content-type", "text/plain"),
        ]

        start_response(status, response_headers)

        for item in output:
            yield item
    return application


def echo_body(environ, start_response):
    status = "200 OK"
    output = environ["wsgi.input"].read()

    response_headers = [
        ("Content-type", "text/plain"),
    ]

    start_response(status, response_headers)

    return [output]


def echo_body_with_response_stream(environ, start_response):
    status = "200 OK"

    response_headers = [("Content-Type", "text/plain")]

    start_response(status, response_headers)

    def output_generator(f):
        while True:
            output = f.read(2)
            if not output:
                break
            yield output

    return output_generator(f=environ["wsgi.input"])


def raise_exc(environ, start_response):
    status = "500 Server Error"
    output = b"Nope!"

    response_headers = [
        ("Content-type", "text/plain"),
    ]

    try:
        raise ValueError()
    except ValueError:
        exc_info = sys.exc_info()
        start_response(status, response_headers, exc_info=exc_info)

    return [output]


def test_wsgi():
    client = httpx.Client(app=application_factory([b"Hello, World!"]))
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_wsgi_upload():
    client = httpx.Client(app=echo_body)
    response = client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


def test_wsgi_upload_with_response_stream():
    client = httpx.Client(app=echo_body_with_response_stream)
    response = client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


def test_wsgi_exc():
    client = httpx.Client(app=raise_exc)
    with pytest.raises(ValueError):
        client.get("http://www.example.org/")


def test_wsgi_generator():
    output = [b"", b"", b"Some content", b" and more content"]
    client = httpx.Client(app=application_factory(output))
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Some content and more content"
    assert response.content == b"Some content and more content"
