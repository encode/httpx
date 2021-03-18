import json

import pytest

import httpx


async def hello_world(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_path(scope, receive, send):
    status = 200
    output = json.dumps({"path": scope["path"]}).encode("utf-8")
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_raw_path(scope, receive, send):
    status = 200
    output = json.dumps({"raw_path": scope["raw_path"].decode("ascii")}).encode("utf-8")
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


async def echo_headers(scope, receive, send):
    status = 200
    output = json.dumps(
        {"headers": [[k.decode(), v.decode()] for k, v in scope["headers"]]}
    ).encode("utf-8")
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def raise_exc(scope, receive, send):
    raise RuntimeError()


async def raise_exc_after_response(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise RuntimeError()


@pytest.mark.usefixtures("async_environment")
async def test_asgi_transport():
    async with httpx.ASGITransport(app=hello_world) as transport:
        status_code, headers, stream, ext = await transport.arequest(
            b"GET", (b"http", b"www.example.org", 80, b"/")
        )
        body = b"".join([part async for part in stream])

        assert status_code == 200
        assert body == b"Hello, World!"


@pytest.mark.usefixtures("async_environment")
async def test_asgi_transport_no_body():
    async with httpx.ASGITransport(app=echo_body) as transport:
        status_code, headers, stream, ext = await transport.arequest(
            b"GET", (b"http", b"www.example.org", 80, b"/")
        )
        body = b"".join([part async for part in stream])

        assert status_code == 200
        assert body == b""


@pytest.mark.usefixtures("async_environment")
async def test_asgi():
    async with httpx.AsyncClient(app=hello_world) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.usefixtures("async_environment")
async def test_asgi_urlencoded_path():
    async with httpx.AsyncClient(app=echo_path) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"path": "/user@example.org"}


@pytest.mark.usefixtures("async_environment")
async def test_asgi_raw_path():
    async with httpx.AsyncClient(app=echo_raw_path) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"raw_path": "/user%40example.org"}


@pytest.mark.usefixtures("async_environment")
async def test_asgi_upload():
    async with httpx.AsyncClient(app=echo_body) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert response.text == "example"


@pytest.mark.usefixtures("async_environment")
async def test_asgi_headers():
    async with httpx.AsyncClient(app=echo_headers) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.json() == {
        "headers": [
            ["host", "www.example.org"],
            ["accept", "*/*"],
            ["accept-encoding", "gzip, deflate, br"],
            ["connection", "keep-alive"],
            ["user-agent", f"python-httpx/{httpx.__version__}"],
        ]
    }


@pytest.mark.usefixtures("async_environment")
async def test_asgi_exc():
    async with httpx.AsyncClient(app=raise_exc) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.usefixtures("async_environment")
async def test_asgi_exc_after_response():
    async with httpx.AsyncClient(app=raise_exc_after_response) as client:
        with pytest.raises(RuntimeError):
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

    async with httpx.AsyncClient(app=read_body) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert disconnect
