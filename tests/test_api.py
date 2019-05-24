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
    response = httpcore.get("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"


@threadpool
def test_post(server):
    response = httpcore.post("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_post_byte_iterator(server):
    def data():
        yield b"Hello"
        yield b", "
        yield b"world!"

    response = httpcore.post("http://127.0.0.1:8000/", data=data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_options(server):
    response = httpcore.options("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_head(server):
    response = httpcore.head("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_put(server):
    response = httpcore.put("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_patch(server):
    response = httpcore.patch("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_delete(server):
    response = httpcore.delete("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
