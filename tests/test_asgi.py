from functools import partial

import pytest

import httpx


async def hello_world(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_body(scope, receive, send):
    status = 200
    headers = [(b"content-type", "text/plain")]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    more_body = True
    while more_body:
        message = await receive()
        body = message.get("body", b"")
        more_body = message.get("more_body", False)
        await send({"type": "http.response.body", "body": body, "more_body": more_body})


async def raise_exc(scope, receive, send, exc=ValueError):
    raise exc()


async def raise_exc_after_response(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise ValueError()


@pytest.mark.usefixtures("async_environment")
async def test_asgi():
    client = httpx.AsyncClient(app=hello_world)
    response = await client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.usefixtures("async_environment")
async def test_asgi_upload():
    client = httpx.AsyncClient(app=echo_body)
    response = await client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


@pytest.mark.usefixtures("async_environment")
async def test_asgi_exc():
    client = httpx.AsyncClient(app=raise_exc)
    with pytest.raises(ValueError):
        await client.get("http://www.example.org/")


@pytest.mark.usefixtures("async_environment")
async def test_asgi_http_error():
    client = httpx.AsyncClient(app=partial(raise_exc, exc=RuntimeError))
    with pytest.raises(RuntimeError):
        await client.get("http://www.example.org/")


@pytest.mark.usefixtures("async_environment")
async def test_asgi_exc_after_response():
    client = httpx.AsyncClient(app=raise_exc_after_response)
    with pytest.raises(ValueError):
        await client.get("http://www.example.org/")


@pytest.mark.usefixtures("async_environment")
async def test_asgi_disconnect_after_response_complete():
    disconnect = False

    async def read_body(scope, receive, send):
        nonlocal disconnect

        status = 200
        headers = [(b"content-type", "text/plain")]

        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        more_body = True
        while more_body:
            message = await receive()
            more_body = message.get("more_body", False)

        await send({"type": "http.response.body", "body": b"", "more_body": False})

        # The ASGI spec says of the Disconnect message:
        # "Sent to the application when a HTTP connection is closed or if receive is
        # called after a response has been sent."
        # So if receive() is called again, the disconnect message should be received
        message = await receive()
        disconnect = message.get("type") == "http.disconnect"

    client = httpx.AsyncClient(app=read_body)
    response = await client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert disconnect
