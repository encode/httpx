import json
from contextlib import aclosing

import anyio
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


async def hello_world_3_times(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})

    for i in range(3):
        body = b"%d: %s\n" % (i, output)
        await send({"type": "http.response.body", "body": body, "more_body": True})

    else:
        await send({"type": "http.response.body", "body": b"", "more_body": False})


async def hello_world_endlessly(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})

    k = 0
    while True:
        body = b"%d: %s\n" % (k, output)
        await send({"type": "http.response.body", "body": body, "more_body": True})
        k += 1


async def raise_exc(scope, receive, send):
    raise RuntimeError()


async def raise_exc_after_response(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise RuntimeError()


@pytest.mark.anyio
async def test_asgi_transport():
    async with httpx.ASGITransport(app=hello_world) as transport:
        request = httpx.Request("GET", "http://www.example.com/")
        response = await transport.handle_async_request(request)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b"Hello, World!"


@pytest.mark.anyio
async def test_asgi_transport_no_body():
    async with httpx.ASGITransport(app=echo_body) as transport:
        request = httpx.Request("GET", "http://www.example.com/")
        response = await transport.handle_async_request(request)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b""


@pytest.mark.anyio
async def test_asgi():
    async with httpx.AsyncClient(app=hello_world) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.anyio
async def test_asgi_urlencoded_path():
    async with httpx.AsyncClient(app=echo_path) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"path": "/user@example.org"}


@pytest.mark.anyio
async def test_asgi_raw_path():
    async with httpx.AsyncClient(app=echo_raw_path) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"raw_path": "/user@example.org"}


@pytest.mark.anyio
async def test_asgi_upload():
    async with httpx.AsyncClient(app=echo_body) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert response.text == "example"


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_asgi_exc():
    async with httpx.AsyncClient(app=raise_exc) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_exc_after_response():
    async with httpx.AsyncClient(app=raise_exc_after_response) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_asgi_streaming_exhaust():
    "Exhaust resource and verify that it has been closed"
    client = httpx.AsyncClient(app=hello_world_3_times)
    async with client.stream("GET", "http://www.example.org/") as response:
        assert response.status_code == 200
        lines = []

        async with aclosing(response.aiter_lines()) as stream:
            async for line in stream:
                lines.append(line)

            # Should not have any more items left
            with pytest.raises(StopAsyncIteration):
                with anyio.fail_after(0.1):
                    await stream.__anext__()

        assert lines == [
            "0: Hello, World!\n",
            "1: Hello, World!\n",
            "2: Hello, World!\n",
        ]


@pytest.mark.anyio
async def test_asgi_streaming_interrupt_then_continue():
    "Interrupt and then continue consuming"
    client = httpx.AsyncClient(app=hello_world_endlessly)
    async with client.stream("GET", "http://www.example.org/") as response:
        assert response.status_code == 200
        lines = []

        async with aclosing(response.aiter_lines()) as stream:
            async for line in stream:
                if line.startswith("3: "):
                    break
                lines.append(line)

            async for line in stream:
                lines.append(line)
                if line.startswith("4: "):
                    break

        assert lines == [
            "0: Hello, World!\n",
            "1: Hello, World!\n",
            "2: Hello, World!\n",
            "4: Hello, World!\n",
        ]


@pytest.mark.anyio
async def test_asgi_streaming_interrupt_and_resource_cleanup():
    "Interrupt without letting stream be exhausted, make sure resource released after context block"
    client = httpx.AsyncClient(app=hello_world_endlessly)
    async with client.stream("GET", "http://www.example.org/") as response:
        assert response.status_code == 200
        lines = []

        stream = response.aiter_lines()
        async for line in stream:
            if line.startswith("3: "):
                break
            lines.append(line)

        assert lines == [
            "0: Hello, World!\n",
            "1: Hello, World!\n",
            "2: Hello, World!\n",
        ]

    # Make sure resource was released after context block
    with pytest.raises(StopAsyncIteration):
        with anyio.fail_after(0.1):
            await stream.__anext__()


@pytest.mark.anyio
async def test_asgi_streaming_exc():
    client = httpx.AsyncClient(app=raise_exc)
    with pytest.raises(RuntimeError):
        async with client.stream("GET", "http://www.example.org/"):
            pass  # pragma: no cover


@pytest.mark.anyio
async def test_asgi_streaming_exc_after_response():
    client = httpx.AsyncClient(app=raise_exc_after_response)
    with pytest.raises(RuntimeError):
        async with client.stream("GET", "http://www.example.org/") as response:
            async for _ in response.aiter_bytes():
                pass  # pragma: no cover
