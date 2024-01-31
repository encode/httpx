from __future__ import annotations

import sys
import typing
import wsgiref.validate
from functools import partial
from io import StringIO

import pytest

import httpx

if typing.TYPE_CHECKING:  # pragma: no cover
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment


def application_factory(output: typing.Iterable[bytes]) -> WSGIApplication:
    def application(environ, start_response):
        status = "200 OK"

        response_headers = [
            ("Content-type", "text/plain"),
        ]

        start_response(status, response_headers)

        for item in output:
            yield item

    return wsgiref.validate.validator(application)


def echo_body(
    environ: WSGIEnvironment, start_response: StartResponse
) -> typing.Iterable[bytes]:
    status = "200 OK"
    output = environ["wsgi.input"].read()

    response_headers = [
        ("Content-type", "text/plain"),
    ]

    start_response(status, response_headers)

    return [output]


def echo_body_with_response_stream(
    environ: WSGIEnvironment, start_response: StartResponse
) -> typing.Iterable[bytes]:
    status = "200 OK"

    response_headers = [("Content-Type", "text/plain")]

    start_response(status, response_headers)

    def output_generator(f: typing.IO[bytes]) -> typing.Iterator[bytes]:
        while True:
            output = f.read(2)
            if not output:
                break
            yield output

    return output_generator(f=environ["wsgi.input"])


def raise_exc(
    environ: WSGIEnvironment,
    start_response: StartResponse,
    exc: type[Exception] = ValueError,
) -> typing.Iterable[bytes]:
    status = "500 Server Error"
    output = b"Nope!"

    response_headers = [
        ("Content-type", "text/plain"),
    ]

    try:
        raise exc()
    except exc:
        exc_info = sys.exc_info()
        start_response(status, response_headers, exc_info)

    return [output]


def log_to_wsgi_log_buffer(environ, start_response):
    print("test1", file=environ["wsgi.errors"])
    environ["wsgi.errors"].write("test2")
    return echo_body(environ, start_response)


def test_wsgi():
    client = httpx.Client(app=application_factory([b"Hello, World!"]))
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_wsgi_upload():
    client = httpx.Client(app=echo_body)
    response = client.post("http://www.example.org/", content=b"example")
    assert response.status_code == 200
    assert response.text == "example"


def test_wsgi_upload_with_response_stream():
    client = httpx.Client(app=echo_body_with_response_stream)
    response = client.post("http://www.example.org/", content=b"example")
    assert response.status_code == 200
    assert response.text == "example"


def test_wsgi_exc():
    client = httpx.Client(app=raise_exc)
    with pytest.raises(ValueError):
        client.get("http://www.example.org/")


def test_wsgi_http_error():
    client = httpx.Client(app=partial(raise_exc, exc=RuntimeError))
    with pytest.raises(RuntimeError):
        client.get("http://www.example.org/")


def test_wsgi_generator():
    output = [b"", b"", b"Some content", b" and more content"]
    client = httpx.Client(app=application_factory(output))
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Some content and more content"


def test_wsgi_generator_empty():
    output = [b"", b"", b"", b""]
    client = httpx.Client(app=application_factory(output))
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == ""


def test_logging():
    buffer = StringIO()
    transport = httpx.WSGITransport(app=log_to_wsgi_log_buffer, wsgi_errors=buffer)
    client = httpx.Client(transport=transport)
    response = client.post("http://www.example.org/", content=b"example")
    assert response.status_code == 200  # no errors
    buffer.seek(0)
    assert buffer.read() == "test1\ntest2"


@pytest.mark.parametrize(
    "url, expected_server_port",
    [
        pytest.param("http://www.example.org", "80", id="auto-http"),
        pytest.param("https://www.example.org", "443", id="auto-https"),
        pytest.param("http://www.example.org:8000", "8000", id="explicit-port"),
    ],
)
def test_wsgi_server_port(url: str, expected_server_port: str) -> None:
    """
    SERVER_PORT is populated correctly from the requested URL.
    """
    hello_world_app = application_factory([b"Hello, World!"])
    server_port: str | None = None

    def app(environ, start_response):
        nonlocal server_port
        server_port = environ["SERVER_PORT"]
        return hello_world_app(environ, start_response)

    client = httpx.Client(app=app)
    response = client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, World!"
    assert server_port == expected_server_port


def test_wsgi_server_protocol():
    server_protocol = None

    def app(environ, start_response):
        nonlocal server_protocol
        server_protocol = environ["SERVER_PROTOCOL"]
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"success"]

    with httpx.Client(app=app, base_url="http://testserver") as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.text == "success"
    assert server_protocol == "HTTP/1.1"
