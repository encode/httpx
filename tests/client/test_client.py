import asyncio
import functools

import pytest

import httpcore


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
    with httpcore.Client() as http:
        response = http.get("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"
    assert response.protocol == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<SyncResponse(status_code=200)>"


@threadpool
def test_post(server):
    with httpcore.Client() as http:
        response = http.post("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_stream_response(server):
    with httpcore.Client() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    content = response.read()
    assert content == b"Hello, world!"


@threadpool
def test_stream_iterator(server):
    with httpcore.Client() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.stream():
        body += chunk
    assert body == b"Hello, world!"


@threadpool
def test_raw_iterator(server):
    with httpcore.Client() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.raw():
        body += chunk
    assert body == b"Hello, world!"
    response.close()  # TODO: should Response be available as context managers?


@threadpool
def test_options(server):
    with httpcore.SyncClient() as http:
        response = http.options("http://127.0.0.1:8000/")

    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_head(server):
    with httpcore.SyncClient() as http:
        response = http.head("http://127.0.0.1:8000/")

    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_put(server):
    with httpcore.SyncClient() as http:
        response = http.put("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_patch(server):
    with httpcore.SyncClient() as http:
        response = http.patch("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_delete(server):
    with httpcore.SyncClient() as http:
        response = http.delete("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
