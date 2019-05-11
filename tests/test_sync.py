import asyncio
import datetime
import email.utils
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
    with httpcore.SyncClient() as http:
        response = http.get("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"
    assert response.protocol == "HTTP/1.1"
    assert (
        datetime.datetime.now(datetime.timezone.utc)
        - email.utils.parsedate_to_datetime(response.headers["date"])
    ) < datetime.timedelta(seconds=1)
    expected_headers = httpcore.Headers(
        {
            "server": "uvicorn",
            "content-type": "text/plain",
            "transfer-encoding": "chunked",
        }
    )
    for header, value in expected_headers.items():
        assert value == response.headers[header]

    assert repr(response) == "<SyncResponse(status_code=200)>"


@threadpool
def test_post(server):
    with httpcore.SyncClient() as http:
        response = http.post("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@threadpool
def test_stream_response(server):
    with httpcore.SyncClient() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    content = response.read()
    assert content == b"Hello, world!"


@threadpool
def test_stream_iterator(server):
    with httpcore.SyncClient() as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.stream():
        body += chunk
    assert body == b"Hello, world!"


@threadpool
def test_raw_iterator(server):
    with httpcore.SyncClient() as http:
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
