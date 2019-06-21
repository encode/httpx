import asyncio
import functools

import pytest

import http3


def threadpool(func):
    """
    Our sync tests should run in seperate thread to the uvicorn server.
    """

    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        nonlocal func

        loop = asyncio.get_event_loop()
        if kwargs:
            func = functools.partial(func, **kwargs)
        await loop.run_in_executor(None, func, *args)

    return pytest.mark.asyncio(wrapped)


@threadpool
def test_get(server):
    url = "http://127.0.0.1:8000/"
    with http3.Client() as http:
        response = http.get(url)
    assert response.status_code == 200
    assert response.url == http3.URL(url)
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"
    assert response.protocol == "HTTP/1.1"
    assert response.encoding == "iso-8859-1"
    assert response.request.url == http3.URL(url)
    assert response.headers
    assert response.is_redirect is False
    assert repr(response) == "<Response [200 OK])>"


@threadpool
def test_post(server):
    with http3.Client() as http:
        response = http.post("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_post_json(server):
    with http3.Client() as http:
        response = http.post("http://127.0.0.1:8000/", json={"text": "Hello, world!"})
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_stream_response(server):
    with http3.Client() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    content = response.read()
    assert content == b"Hello, world!"


@threadpool
def test_stream_iterator(server):
    with http3.Client() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.stream():
        body += chunk
    assert body == b"Hello, world!"


@threadpool
def test_raw_iterator(server):
    with http3.Client() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.raw():
        body += chunk
    assert body == b"Hello, world!"
    response.close()  # TODO: should Response be available as context managers?


@threadpool
def test_raise_for_status(server):
    with http3.Client() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = client.request(
                "GET", "http://127.0.0.1:8000/status/{}".format(status_code)
            )

            if 400 <= status_code < 600:
                with pytest.raises(http3.exceptions.HttpError):
                    response.raise_for_status()
            else:
                assert response.raise_for_status() is None


@threadpool
def test_options(server):
    with http3.Client() as http:
        response = http.options("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_head(server):
    with http3.Client() as http:
        response = http.head("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_put(server):
    with http3.Client() as http:
        response = http.put("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_patch(server):
    with http3.Client() as http:
        response = http.patch("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_delete(server):
    with http3.Client() as http:
        response = http.delete("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_base_url(server):
    base_url = "http://127.0.0.1:8000/"
    with http3.Client(base_url=base_url) as http:
        response = http.get('/')
    assert response.status_code == 200
    assert str(response.url) == base_url
