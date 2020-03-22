from typing import Callable, Dict

import pytest

import httpx


async def hello_world(scope: Dict, receive: Callable, send: Callable) -> None:
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_body(scope: Dict, receive: Callable, send: Callable) -> None:
    status = 200
    headers = [(b"content-type", "text/plain")]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    more_body = True
    while more_body:
        message = await receive()
        body = message.get("body", b"")
        more_body = message.get("more_body", False)
        await send({"type": "http.response.body", "body": body, "more_body": more_body})


async def raise_exc(scope: Dict, receive: Callable, send: Callable) -> None:
    raise ValueError()


async def raise_exc_after_response(scope: Dict, receive: Callable, send: Callable) -> None:
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise ValueError()


@pytest.mark.asyncio
async def test_asgi() -> None:
    client = httpx.AsyncClient(app=hello_world)
    response = await client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.asyncio
async def test_asgi_upload() -> None:
    client = httpx.AsyncClient(app=echo_body)
    response = await client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


@pytest.mark.asyncio
async def test_asgi_exc() -> None:
    client = httpx.AsyncClient(app=raise_exc)
    with pytest.raises(ValueError):
        await client.get("http://www.example.org/")


@pytest.mark.asyncio
async def test_asgi_exc_after_response() -> None:
    client = httpx.AsyncClient(app=raise_exc_after_response)
    with pytest.raises(ValueError):
        await client.get("http://www.example.org/")
