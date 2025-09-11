from __future__ import annotations

import contextvars
import json
import typing

import anyio
import pytest

import httpx

test_asgi_contextvar: contextvars.ContextVar[str] = contextvars.ContextVar(
    "test_asgi_contextvar"
)


@pytest.fixture(params=[False, True], ids=["no_streaming", "with_streaming"])
def streaming(request):
    return request.param


def run_in_task_group(
    app: typing.Callable[..., typing.Awaitable[None]],
) -> typing.Callable[..., typing.Awaitable[None]]:
    """A decorator that runs an ASGI callable in a task group"""

    async def wrapped_app(*args):
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(app, *args)

    return wrapped_app


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


async def raise_exc_after_response_start(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    raise RuntimeError()


async def raise_exc_after_response(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise RuntimeError()


@pytest.mark.anyio
async def test_asgi_transport(streaming):
    async with httpx.ASGITransport(app=hello_world, streaming=streaming) as transport:
        request = httpx.Request("GET", "http://www.example.com/")
        response = await transport.handle_async_request(request)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b"Hello, World!"


@pytest.mark.anyio
async def test_asgi_transport_no_body(streaming):
    async with httpx.ASGITransport(app=echo_body, streaming=streaming) as transport:
        request = httpx.Request("GET", "http://www.example.com/")
        response = await transport.handle_async_request(request)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b""


@pytest.mark.anyio
async def test_asgi(streaming):
    transport = httpx.ASGITransport(app=hello_world, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.anyio
async def test_asgi_urlencoded_path(streaming):
    transport = httpx.ASGITransport(app=echo_path, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"path": "/user@example.org"}


@pytest.mark.anyio
async def test_asgi_raw_path(streaming):
    transport = httpx.ASGITransport(app=echo_raw_path, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"raw_path": "/user@example.org"}


@pytest.mark.anyio
async def test_asgi_raw_path_should_not_include_querystring_portion(streaming):
    """
    See https://github.com/encode/httpx/issues/2810
    """
    transport = httpx.ASGITransport(app=echo_raw_path, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        url = httpx.URL("http://www.example.org/path?query")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"raw_path": "/path"}


@pytest.mark.anyio
async def test_asgi_upload(streaming):
    transport = httpx.ASGITransport(app=echo_body, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert response.text == "example"


@pytest.mark.anyio
async def test_asgi_headers(streaming):
    transport = httpx.ASGITransport(app=echo_headers, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.json() == {
        "headers": [
            ["host", "www.example.org"],
            ["accept", "*/*"],
            ["accept-encoding", "gzip, deflate, br, zstd"],
            ["connection", "keep-alive"],
            ["user-agent", f"python-httpx/{httpx.__version__}"],
        ]
    }


@pytest.mark.anyio
async def test_asgi_exc(streaming):
    transport = httpx.ASGITransport(app=raise_exc, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_exc_after_response_start(streaming):
    transport = httpx.ASGITransport(
        app=raise_exc_after_response_start, streaming=streaming
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_exc_after_response(streaming):
    transport = httpx.ASGITransport(app=raise_exc_after_response, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_disconnect_after_response_complete(streaming):
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

    transport = httpx.ASGITransport(app=read_body, streaming=streaming)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert disconnect


@pytest.mark.anyio
async def test_asgi_exc_no_raise(streaming):
    transport = httpx.ASGITransport(
        app=raise_exc, raise_app_exceptions=False, streaming=streaming
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 500


@pytest.mark.anyio
async def test_asgi_exc_no_raise_after_response_start(streaming):
    transport = httpx.ASGITransport(
        app=raise_exc_after_response_start,
        raise_app_exceptions=False,
        streaming=streaming,
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 200


@pytest.mark.anyio
async def test_asgi_exc_no_raise_after_response(streaming):
    transport = httpx.ASGITransport(
        app=raise_exc_after_response, raise_app_exceptions=False, streaming=streaming
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 200


@pytest.mark.anyio
async def test_asgi_app_runs_in_same_context_as_caller():
    async def set_contextvar_in_app(scope, receive, send):
        test_asgi_contextvar.set("value_from_app")

        status = 200
        output = b"Hello, World!"
        headers = [
            (b"content-type", "text/plain"),
            (b"content-length", str(len(output))),
        ]

        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await send({"type": "http.response.body", "body": output})

    transport = httpx.ASGITransport(
        app=set_contextvar_in_app, raise_app_exceptions=False, streaming=False
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 200

        assert test_asgi_contextvar.get(None) == "value_from_app"


@pytest.mark.parametrize(
    "send_in_sub_task",
    [pytest.param(False, id="no_sub_task"), pytest.param(True, id="with_sub_task")],
)
@pytest.mark.anyio
async def test_asgi_stream_returns_before_waiting_for_body(send_in_sub_task):
    start_response_body = anyio.Event()

    async def send_response_body_after_event(scope, receive, send):
        status = 200
        headers = [(b"content-type", b"text/plain")]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await start_response_body.wait()
        await send({"type": "http.response.body", "body": b"body", "more_body": False})

    if send_in_sub_task:
        send_response_body_after_event = run_in_task_group(
            send_response_body_after_event
        )

    transport = httpx.ASGITransport(app=send_response_body_after_event, streaming=True)
    async with httpx.AsyncClient(transport=transport) as client:
        with anyio.fail_after(0.1):
            async with client.stream("GET", "http://www.example.org/") as response:
                assert response.status_code == 200
                start_response_body.set()
                await response.aread()
                assert response.text == "body"


@pytest.mark.parametrize(
    "send_in_sub_task",
    [pytest.param(False, id="no_sub_task"), pytest.param(True, id="with_sub_task")],
)
@pytest.mark.anyio
async def test_asgi_stream_allows_iterative_streaming(send_in_sub_task):
    stream_events = [anyio.Event() for i in range(4)]

    async def send_response_body_after_event(scope, receive, send):
        status = 200
        headers = [(b"content-type", b"text/plain")]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        for e in stream_events:
            await e.wait()
            await send(
                {
                    "type": "http.response.body",
                    "body": b"chunk",
                    "more_body": e is not stream_events[-1],
                }
            )

    if send_in_sub_task:
        send_response_body_after_event = run_in_task_group(
            send_response_body_after_event
        )

    transport = httpx.ASGITransport(app=send_response_body_after_event, streaming=True)
    async with httpx.AsyncClient(transport=transport) as client:
        with anyio.fail_after(0.1):
            async with client.stream("GET", "http://www.example.org/") as response:
                assert response.status_code == 200
                iterator = response.aiter_raw()
                for e in stream_events:
                    e.set()
                    assert await iterator.__anext__() == b"chunk"
                with pytest.raises(StopAsyncIteration):
                    await iterator.__anext__()
