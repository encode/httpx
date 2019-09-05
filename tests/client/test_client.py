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


def test_build_request(server):
    url = server.url
    with httpx.Client() as http:
        request = http.build_request("GET", url)
        response = http.send(request)
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


def test_post(server):
    with httpx.Client() as http:
        response = http.post(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_post_json(server):
    with httpx.Client() as http:
        response = http.post(server.url, json={"text": "Hello, world!"})
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_stream_response(server):
    with httpx.Client() as http:
        response = http.get(server.url, stream=True)
    assert response.status_code == 200
    content = response.read()
    assert content == b"Hello, world!"


def test_stream_iterator(server):
    with httpx.Client() as http:
        response = http.get(server.url, stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.stream():
        body += chunk
    assert body == b"Hello, world!"


def test_raw_iterator(server):
    with httpx.Client() as http:
        response = http.get(server.url, stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.raw():
        body += chunk
    assert body == b"Hello, world!"
    response.close()  # TODO: should Response be available as context managers?


def test_raise_for_status(server):
    with httpx.Client() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = client.request(
                "GET", server.url.copy_with(path="/status/{}".format(status_code))
            )
            if 400 <= status_code < 600:
                with pytest.raises(httpx.exceptions.HTTPError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None


def test_options(server):
    with httpx.Client() as http:
        response = http.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_head(server):
    with httpx.Client() as http:
        response = http.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_put(server):
    with httpx.Client() as http:
        response = http.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_patch(server):
    with httpx.Client() as http:
        response = http.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_delete(server):
    with httpx.Client() as http:
        response = http.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_base_url(server):
    base_url = server.url
    with httpx.Client(base_url=base_url) as http:
        response = http.get("/")
    assert response.status_code == 200
    assert response.url == base_url


def test_merge_url():
    client = httpx.Client(base_url="https://www.paypal.com/")
    url = client.merge_url("http://www.paypal.com")

    assert url.scheme == "https"
    assert url.is_ssl


class DerivedFromAsyncioBackend(httpx.AsyncioBackend):
    pass


class AnyBackend:
    pass


def test_client_backend_must_be_asyncio_based():
    httpx.Client(backend=httpx.AsyncioBackend())
    httpx.Client(backend=DerivedFromAsyncioBackend())

    with pytest.raises(ValueError):
        httpx.Client(backend=AnyBackend())
