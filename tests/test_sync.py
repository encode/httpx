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
    assert response.body == b"Hello, world!"


@threadpool
def test_post(server):
    with httpcore.SyncConnectionPool() as http:
        response = http.request("POST", "http://127.0.0.1:8000/", body=b"Hello, world!")
    assert response.status_code == 200
