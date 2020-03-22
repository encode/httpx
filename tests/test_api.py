import typing

import pytest
from uvicorn.main import Server

import httpx


def test_get(server: Server) -> None:
    response = httpx.get(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


def test_post(server: Server) -> None:
    response = httpx.post(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_post_byte_iterator(server: Server) -> None:
    def data() -> typing.Generator[bytes, None, None]:
        yield b"Hello"
        yield b", "
        yield b"world!"

    response = httpx.post(server.url, data=data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_options(server: Server) -> None:
    response = httpx.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_head(server: Server) -> None:
    response = httpx.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_put(server: Server) -> None:
    response = httpx.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_patch(server: Server) -> None:
    response = httpx.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_delete(server: Server) -> None:
    response = httpx.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_stream(server: Server) -> None:
    with httpx.stream("GET", server.url) as response:
        response.read()

    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_get_invalid_url(server: Server) -> None:
    with pytest.raises(httpx.InvalidURL):
        await httpx.get("invalid://example.org")  # type:ignore
