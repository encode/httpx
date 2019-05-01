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
    with httpcore.SyncConnectionPool() as http:
        response = http.request("GET", "http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"


@threadpool
def test_post(server):
    with httpcore.SyncConnectionPool() as http:
        response = http.request("POST", "http://127.0.0.1:8000/", body=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_stream_response(server):
    with httpcore.SyncConnectionPool() as http:
        response = http.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    content = response.read()
    assert content == b"Hello, world!"


@threadpool
def test_stream_iterator(server):
    with httpcore.SyncConnectionPool() as http:
        response = http.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    content = b""
    for chunk in response.stream():
        content += chunk
    assert content == b"Hello, world!"
