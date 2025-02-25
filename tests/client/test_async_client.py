from __future__ import annotations

import typing
from datetime import timedelta

import pytest

import httpx


@pytest.mark.anyio
async def test_get(server):
    url = server.url
    async with httpx.AsyncClient(http2=True) as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    assert response.headers
    assert repr(response) == "<Response [200 OK]>"
    assert response.elapsed > timedelta(seconds=0)


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("invalid://example.org", id="scheme-not-http(s)"),
        pytest.param("://example.org", id="no-scheme"),
        pytest.param("http://", id="no-host"),
    ],
)
@pytest.mark.anyio
async def test_get_invalid_url(server, url):
    async with httpx.AsyncClient() as client:
        with pytest.raises((httpx.UnsupportedProtocol, httpx.LocalProtocolError)):
            await client.get(url)


@pytest.mark.anyio
async def test_build_request(server):
    url = server.url.copy_with(path="/echo_headers")
    headers = {"Custom-header": "value"}
    async with httpx.AsyncClient() as client:
        request = client.build_request("GET", url)
        request.headers.update(headers)
        response = await client.send(request)

    assert response.status_code == 200
    assert response.url == url

    assert response.json()["Custom-header"] == "value"


@pytest.mark.anyio
async def test_post(server):
    url = server.url
    async with httpx.AsyncClient() as client:
        response = await client.post(url, content=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_post_json(server):
    url = server.url
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={"text": "Hello, world!"})
    assert response.status_code == 200


@pytest.mark.anyio
async def test_stream_response(server):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", server.url) as response:
            body = await response.aread()

    assert response.status_code == 200
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


@pytest.mark.anyio
async def test_access_content_stream_response(server):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", server.url) as response:
            pass

    assert response.status_code == 200
    with pytest.raises(httpx.ResponseNotRead):
        response.content  # noqa: B018


@pytest.mark.anyio
async def test_stream_request(server):
    async def hello_world() -> typing.AsyncIterator[bytes]:
        yield b"Hello, "
        yield b"world!"

    async with httpx.AsyncClient() as client:
        response = await client.post(server.url, content=hello_world())
    assert response.status_code == 200


@pytest.mark.anyio
async def test_cannot_stream_sync_request(server):
    def hello_world() -> typing.Iterator[bytes]:  # pragma: no cover
        yield b"Hello, "
        yield b"world!"

    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError):
            await client.post(server.url, content=hello_world())


@pytest.mark.anyio
async def test_raise_for_status(server):
    async with httpx.AsyncClient() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", server.url.copy_with(path=f"/status/{status_code}")
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is response


@pytest.mark.anyio
async def test_options(server):
    async with httpx.AsyncClient() as client:
        response = await client.options(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.anyio
async def test_head(server):
    async with httpx.AsyncClient() as client:
        response = await client.head(server.url)
    assert response.status_code == 200
    assert response.text == ""


@pytest.mark.anyio
async def test_put(server):
    async with httpx.AsyncClient() as client:
        response = await client.put(server.url, content=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_patch(server):
    async with httpx.AsyncClient() as client:
        response = await client.patch(server.url, content=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_delete(server):
    async with httpx.AsyncClient() as client:
        response = await client.delete(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.anyio
async def test_100_continue(server):
    headers = {"Expect": "100-continue"}
    content = b"Echo request body"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            server.url.copy_with(path="/echo_body"), headers=headers, content=content
        )

    assert response.status_code == 200
    assert response.content == content


@pytest.mark.anyio
async def test_context_managed_transport():
    class Transport(httpx.AsyncBaseTransport):
        def __init__(self) -> None:
            self.events: list[str] = []

        async def aclose(self):
            # The base implementation of httpx.AsyncBaseTransport just
            # calls into `.aclose`, so simple transport cases can just override
            # this method for any cleanup, where more complex cases
            # might want to additionally override `__aenter__`/`__aexit__`.
            self.events.append("transport.aclose")

        async def __aenter__(self):
            await super().__aenter__()
            self.events.append("transport.__aenter__")

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            self.events.append("transport.__aexit__")

    transport = Transport()
    async with httpx.AsyncClient(transport=transport):
        pass

    assert transport.events == [
        "transport.__aenter__",
        "transport.aclose",
        "transport.__aexit__",
    ]


@pytest.mark.anyio
async def test_context_managed_transport_and_mount():
    class Transport(httpx.AsyncBaseTransport):
        def __init__(self, name: str) -> None:
            self.name: str = name
            self.events: list[str] = []

        async def aclose(self):
            # The base implementation of httpx.AsyncBaseTransport just
            # calls into `.aclose`, so simple transport cases can just override
            # this method for any cleanup, where more complex cases
            # might want to additionally override `__aenter__`/`__aexit__`.
            self.events.append(f"{self.name}.aclose")

        async def __aenter__(self):
            await super().__aenter__()
            self.events.append(f"{self.name}.__aenter__")

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            self.events.append(f"{self.name}.__aexit__")

    transport = Transport(name="transport")
    mounted = Transport(name="mounted")
    async with httpx.AsyncClient(
        transport=transport, mounts={"http://www.example.org": mounted}
    ):
        pass

    assert transport.events == [
        "transport.__aenter__",
        "transport.aclose",
        "transport.__aexit__",
    ]
    assert mounted.events == [
        "mounted.__aenter__",
        "mounted.aclose",
        "mounted.__aexit__",
    ]


def hello_world(request):
    return httpx.Response(200, text="Hello, world!")


@pytest.mark.anyio
async def test_client_closed_state_using_implicit_open():
    client = httpx.AsyncClient(transport=httpx.MockTransport(hello_world))

    assert not client.is_closed
    await client.get("http://example.com")

    assert not client.is_closed
    await client.aclose()

    assert client.is_closed
    # Once we're close we cannot make any more requests.
    with pytest.raises(RuntimeError):
        await client.get("http://example.com")

    # Once we're closed we cannot reopen the client.
    with pytest.raises(RuntimeError):
        async with client:
            pass  # pragma: no cover


@pytest.mark.anyio
async def test_client_closed_state_using_with_block():
    async with httpx.AsyncClient(transport=httpx.MockTransport(hello_world)) as client:
        assert not client.is_closed
        await client.get("http://example.com")

    assert client.is_closed
    with pytest.raises(RuntimeError):
        await client.get("http://example.com")


def unmounted(request: httpx.Request) -> httpx.Response:
    data = {"app": "unmounted"}
    return httpx.Response(200, json=data)


def mounted(request: httpx.Request) -> httpx.Response:
    data = {"app": "mounted"}
    return httpx.Response(200, json=data)


@pytest.mark.anyio
async def test_mounted_transport():
    transport = httpx.MockTransport(unmounted)
    mounts = {"custom://": httpx.MockTransport(mounted)}

    async with httpx.AsyncClient(transport=transport, mounts=mounts) as client:
        response = await client.get("https://www.example.com")
        assert response.status_code == 200
        assert response.json() == {"app": "unmounted"}

        response = await client.get("custom://www.example.com")
        assert response.status_code == 200
        assert response.json() == {"app": "mounted"}


@pytest.mark.anyio
async def test_async_mock_transport():
    async def hello_world(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Hello, world!")

    transport = httpx.MockTransport(hello_world)

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://www.example.com")
        assert response.status_code == 200
        assert response.text == "Hello, world!"


@pytest.mark.anyio
async def test_cancellation_during_stream():
    """
    If any BaseException is raised during streaming the response, then the
    stream should be closed.

    This includes:

    * `asyncio.CancelledError` (A subclass of BaseException from Python 3.8 onwards.)
    * `trio.Cancelled`
    * `KeyboardInterrupt`
    * `SystemExit`

    See https://github.com/encode/httpx/issues/2139
    """
    stream_was_closed = False

    def response_with_cancel_during_stream(request):
        class CancelledStream(httpx.AsyncByteStream):
            async def __aiter__(self) -> typing.AsyncIterator[bytes]:
                yield b"Hello"
                raise KeyboardInterrupt()
                yield b", world"  # pragma: no cover

            async def aclose(self) -> None:
                nonlocal stream_was_closed
                stream_was_closed = True

        return httpx.Response(
            200, headers={"Content-Length": "12"}, stream=CancelledStream()
        )

    transport = httpx.MockTransport(response_with_cancel_during_stream)

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(KeyboardInterrupt):
            await client.get("https://www.example.com")
        assert stream_was_closed


@pytest.mark.anyio
async def test_server_extensions(server):
    url = server.url
    async with httpx.AsyncClient(http2=True) as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.extensions["http_version"] == b"HTTP/1.1"

async def test_areconnect_reduce_disconnects_and_expiry_present(capfd):
    """
    Test when reduce_disconnects is True and keepalive_expiry is not None.
    Verifies that keepalive_expiry is reduced and print statement is executed.
    """
    mock_pool = AsyncMock(spec=httpcore.AsyncConnectionPool)
    mock_pool._keepalive_expiry = 60  # Set a non-None keepalive_expiry
    transport = AsyncHTTPTransport(reduce_disconnects=True)
    transport._pool = mock_pool
    transport.reduce_timeout_factor = 2

    await transport.areconnect()

    mock_pool.aclose.assert_called_once()
    assert mock_pool._keepalive_expiry == 30  # 60 // 2
    captured = capfd.readouterr()
    assert "Attempt to reduce future disconnects" in captured.out
    assert "by reducing timeout by a facotr of 2" in captured.out


async def test_areconnect_reduce_disconnects_false():
    """
    Test when reduce_disconnects is False.
    Verifies that keepalive_expiry is not reduced.
    """
    mock_pool = AsyncMock(spec=httpcore.AsyncConnectionPool)
    mock_pool._keepalive_expiry = 60
    transport = AsyncHTTPTransport(reduce_disconnects=False)
    transport._pool = mock_pool
    original_expiry = mock_pool._keepalive_expiry

    await transport.areconnect()

    mock_pool.aclose.assert_called_once()
    assert mock_pool._keepalive_expiry == original_expiry # Expiry should remain unchanged


async def test_areconnect_no_keepalive_expiry():
    """
    Test when _keepalive_expiry is None.
    Verifies that keepalive_expiry is not reduced.
    """
    mock_pool = AsyncMock(spec=httpcore.AsyncConnectionPool)
    mock_pool._keepalive_expiry = None  # Set keepalive_expiry to None
    transport = AsyncHTTPTransport(reduce_disconnects=True) # reduce_disconnects is True, but should not matter
    transport._pool = mock_pool
    original_expiry = mock_pool._keepalive_expiry

    await transport.areconnect()

    mock_pool.aclose.assert_called_once()
    assert mock_pool._keepalive_expiry is original_expiry # Expiry should remain None


# -------------------- Tests for handle_async_request method (lines 422-431) --------------------

async def test_handle_async_request_remote_protocol_error_handle_disconnects_true(capfd):
    """
    Test RemoteProtocolError with handle_disconnects=True.
    Verifies reconnection attempt and successful second request.
    """
    mock_pool = AsyncMock(spec=httpcore.AsyncConnectionPool)
    mock_pool.handle_async_request.side_effect = [
        httpcore.RemoteProtocolError("Simulated RemoteProtocolError"),
        AsyncMock(spec=httpcore.Response),  # Mock successful response on retry
    ]
    transport = AsyncHTTPTransport(handle_disconnects=True)
    transport._pool = mock_pool

    request = httpx.Request("GET", "http://example.com")
    await transport.handle_async_request(request)

    assert mock_pool.handle_async_request.call_count == 2  # Called twice (initial + retry)
    mock_pool.aclose.assert_called_once() # areconnect() should call aclose
    captured = capfd.readouterr()
    assert "Reconnection Attempt Successful" in captured.out


async def test_handle_async_request_remote_protocol_error_handle_disconnects_false():
    """
    Test RemoteProtocolError with handle_disconnects=False.
    Verifies exception is re-raised.
    """
    mock_pool = AsyncMock(spec=httpcore.AsyncConnectionPool)
    mock_pool.handle_async_request.side_effect = httpcore.RemoteProtocolError("Simulated RemoteProtocolError")
    transport = AsyncHTTPTransport(handle_disconnects=False)
    transport._pool = mock_pool

    request = httpx.Request("GET", "http://example.com")
    with pytest.raises(httpx.RemoteProtocolError, match="Simulated RemoteProtocolError"):
        await transport.handle_async_request(request)

    mock_pool.handle_async_request.assert_called_once() # Called only once, no retry
    mock_pool.aclose.assert_not_called() # areconnect() and thus aclose() should not be called


async def test_handle_async_request_no_error():
    """
    Test handle_async_request when no RemoteProtocolError occurs.
    Verifies normal execution path.
    """
    mock_pool = AsyncMock(spec=httpcore.AsyncConnectionPool)
    mock_pool.handle_async_request.return_value = AsyncMock(spec=httpcore.Response) # Mock successful response
    transport = AsyncHTTPTransport(handle_disconnects=True) # handle_disconnects doesn't matter here
    transport._pool = mock_pool

    request = httpx.Request("GET", "http://example.com")
    await transport.handle_async_request(request)

    mock_pool.handle_async_request.assert_called_once() # Called once for the initial request
    mock_pool.aclose.assert_not_called() # areconnect() should not be called