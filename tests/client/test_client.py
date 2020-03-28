from datetime import timedelta

import pytest

import httpx


def test_get(server):
    url = server.url
    with httpx.Client() as http:
        response = http.get(url)
    assert response.status_code == 200
    assert response.url == url
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.encoding == "iso-8859-1"
    assert response.request.url == url
    assert response.headers
    assert response.is_redirect is False
    assert repr(response) == "<Response [200 OK]>"
    assert response.elapsed > timedelta(0)


def test_build_request(server):
    url = server.url.copy_with(path="/echo_headers")
    headers = {"Custom-header": "value"}

    with httpx.Client() as client:
        request = client.build_request("GET", url)
        request.headers.update(headers)
        response = client.send(request)

    assert response.status_code == 200
    assert response.url == url

    assert response.json()["Custom-header"] == "value"


def test_post(server):
    with httpx.Client() as client:
        response = client.post(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_post_json(server):
    with httpx.Client() as client:
        response = client.post(server.url, json={"text": "Hello, world!"})
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_stream_response(server):
    with httpx.Client() as client:
        with client.stream("GET", server.url) as response:
            content = response.read()
    assert response.status_code == 200
    assert content == b"Hello, world!"


def test_stream_iterator(server):
    body = b""

    with httpx.Client() as client:
        with client.stream("GET", server.url) as response:
            for chunk in response.iter_bytes():
                body += chunk

    assert response.status_code == 200
    assert body == b"Hello, world!"


def test_raw_iterator(server):
    body = b""

    with httpx.Client() as client:
        with client.stream("GET", server.url) as response:
            for chunk in response.iter_raw():
                body += chunk

    assert response.status_code == 200
    assert body == b"Hello, world!"


def test_raise_for_status(server):
    with httpx.Client() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = client.request(
                "GET", server.url.copy_with(path="/status/{}".format(status_code))
            )
            if 400 <= status_code < 600:
                with pytest.raises(httpx.HTTPError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None


def test_options(server):
    with httpx.Client() as client:
        response = client.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_head(server):
    with httpx.Client() as client:
        response = client.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_put(server):
    with httpx.Client() as client:
        response = client.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_patch(server):
    with httpx.Client() as client:
        response = client.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_delete(server):
    with httpx.Client() as client:
        response = client.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_base_url(server):
    base_url = server.url
    with httpx.Client(base_url=base_url) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.url == base_url


def test_merge_url():
    client = httpx.Client(base_url="https://www.paypal.com/")
    url = client.merge_url("http://www.paypal.com")

    assert url.scheme == "https"
    assert url.is_ssl


def test_elapsed_delay(server):
    url = server.url.copy_with(path="/slow_response/100")
    with httpx.Client() as client:
        response = client.get(url)
    assert response.elapsed.total_seconds() > 0.0


def test_wsgi_app_generator():
    def application(env, start_response):
        body = b"""


<!DOCTYPE html>
<html>
  <head>
    <title>This is not a web page</title>
  </head>
  <body>
    <p>This page deliberately left blank</p>
  </body>
</html>
"""
        start_response('200 OK', [('Content-Type','text/html')])
        for line in body.split(b"\n"):
            yield line

    with httpx.Client(app=application) as client:
        response = client.get("http://example.com/")
        assert b"This page deliberately left blank" in response.content
