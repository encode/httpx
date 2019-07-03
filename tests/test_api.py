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
    response = http3.get("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"


@threadpool
def test_post(server):
    response = http3.post("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_post_byte_iterator(server):
    def data():
        yield b"Hello"
        yield b", "
        yield b"world!"

    response = http3.post("http://127.0.0.1:8000/", data=data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_options(server):
    response = http3.options("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_head(server):
    response = http3.head("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_put(server):
    response = http3.put("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_patch(server):
    response = http3.patch("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_delete(server):
    response = http3.delete("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_get_invalid_url(server):
    with pytest.raises(http3.InvalidURL):
        http3.get("invalid://example.org")
