from __future__ import annotations

import typing
from datetime import timedelta

import pytest

import httpx


def test_get(server):
    url = server.url
    with httpx.Client(http2=True) as client:
        response = client.get(url)
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
def test_get_invalid_url(server, url):
    with httpx.Client() as client:
        with pytest.raises((httpx.UnsupportedProtocol, httpx.LocalProtocolError)):
            client.get(url)


def test_build_request(server):
    url = server.url.copy_with(path="/echo_headers")
    headers = {"Custom-header": "value"}
    with httpx.Client() as client:
        request = client.build_request("GET", url)
        request.headers.update(headers)
        response = client.send(request)

    assert response.status_code == 200
    assert response.url == url

    assert response.json()["Custom-header"] == "value"


def test_post(server):
    url = server.url
    with httpx.Client() as client:
        response = client.post(url, content=b"Hello, world!")
    assert response.status_code == 200


def test_post_json(server):
    url = server.url
    with httpx.Client() as client:
        response = client.post(url, json={"text": "Hello, world!"})
    assert response.status_code == 200


def test_stream_response(server):
    with httpx.Client() as client:
        with client.stream("GET", server.url) as response:
            body = response.read()

    assert response.status_code == 200
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


def test_access_content_stream_response(server):
    with httpx.Client() as client:
        with client.stream("GET", server.url) as response:
            pass

    assert response.status_code == 200
    with pytest.raises(httpx.ResponseNotRead):
        response.content  # noqa: B018


def test_stream_request(server):
    def hello_world() -> typing.Iterator[bytes]:
        yield b"Hello, "
        yield b"world!"

    with httpx.Client() as client:
        response = client.post(server.url, content=hello_world())
    assert response.status_code == 200


def test_raise_for_status(server):
    with httpx.Client() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = client.request(
                "GET", server.url.copy_with(path=f"/status/{status_code}")
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is response


def test_options(server):
    with httpx.Client() as client:
        response = client.options(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_head(server):
    with httpx.Client() as client:
        response = client.head(server.url)
    assert response.status_code == 200
    assert response.text == ""


def test_put(server):
    with httpx.Client() as client:
        response = client.put(server.url, content=b"Hello, world!")
    assert response.status_code == 200


def test_patch(server):
    with httpx.Client() as client:
        response = client.patch(server.url, content=b"Hello, world!")
    assert response.status_code == 200


def test_delete(server):
    with httpx.Client() as client:
        response = client.delete(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_100_continue(server):
    headers = {"Expect": "100-continue"}
    content = b"Echo request body"

    with httpx.Client() as client:
        response = client.post(
            server.url.copy_with(path="/echo_body"), headers=headers, content=content
        )

    assert response.status_code == 200
    assert response.content == content


def test_context_managed_transport():
    class Transport(httpx.BaseTransport):
        def __init__(self) -> None:
            self.events: list[str] = []

        def close(self):
            # The base implementation of httpx.BaseTransport just
            # calls into `.close`, so simple transport cases can just override
            # this method for any cleanup, where more complex cases
            # might want to additionally override `__enter__`/`__exit__`.
            self.events.append("transport.close")

        def __enter__(self):
            super().__enter__()
            self.events.append("transport.__enter__")

        def __exit__(self, *args):
            super().__exit__(*args)
            self.events.append("transport.__exit__")

    transport = Transport()
    with httpx.Client(transport=transport):
        pass

    assert transport.events == [
        "transport.__enter__",
        "transport.close",
        "transport.__exit__",
    ]


def test_context_managed_transport_and_mount():
    class Transport(httpx.BaseTransport):
        def __init__(self, name: str) -> None:
            self.name: str = name
            self.events: list[str] = []

        def close(self):
            # The base implementation of httpx.BaseTransport just
            # calls into `.close`, so simple transport cases can just override
            # this method for any cleanup, where more complex cases
            # might want to additionally override `__enter__`/`__exit__`.
            self.events.append(f"{self.name}.close")

        def __enter__(self):
            super().__enter__()
            self.events.append(f"{self.name}.__enter__")

        def __exit__(self, *args):
            super().__exit__(*args)
            self.events.append(f"{self.name}.__exit__")

    transport = Transport(name="transport")
    mounted = Transport(name="mounted")
    with httpx.Client(transport=transport, mounts={"http://www.example.org": mounted}):
        pass

    assert transport.events == [
        "transport.__enter__",
        "transport.close",
        "transport.__exit__",
    ]
    assert mounted.events == [
        "mounted.__enter__",
        "mounted.close",
        "mounted.__exit__",
    ]


def hello_world(request):
    return httpx.Response(200, text="Hello, world!")


def test_client_closed_state_using_implicit_open():
    client = httpx.Client(transport=httpx.MockTransport(hello_world))

    assert not client.is_closed
    client.get("http://example.com")

    assert not client.is_closed
    client.close()

    assert client.is_closed
    # Once we're close we cannot make any more requests.
    with pytest.raises(RuntimeError):
        client.get("http://example.com")

    # Once we're closed we cannot reopen the client.
    with pytest.raises(RuntimeError):
        with client:
            pass  # pragma: no cover


def test_client_closed_state_using_with_block():
    with httpx.Client(transport=httpx.MockTransport(hello_world)) as client:
        assert not client.is_closed
        client.get("http://example.com")

    assert client.is_closed
    with pytest.raises(RuntimeError):
        client.get("http://example.com")


def unmounted(request: httpx.Request) -> httpx.Response:
    data = {"app": "unmounted"}
    return httpx.Response(200, json=data)


def mounted(request: httpx.Request) -> httpx.Response:
    data = {"app": "mounted"}
    return httpx.Response(200, json=data)


def test_mounted_transport():
    transport = httpx.MockTransport(unmounted)
    mounts = {"custom://": httpx.MockTransport(mounted)}

    with httpx.Client(transport=transport, mounts=mounts) as client:
        response = client.get("https://www.example.com")
        assert response.status_code == 200
        assert response.json() == {"app": "unmounted"}

        response = client.get("custom://www.example.com")
        assert response.status_code == 200
        assert response.json() == {"app": "mounted"}


def test_mock_transport():
    def hello_world(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Hello, world!")

    transport = httpx.MockTransport(hello_world)

    with httpx.Client(transport=transport) as client:
        response = client.get("https://www.example.com")
        assert response.status_code == 200
        assert response.text == "Hello, world!"


def test_cancellation_during_stream():
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
        class CancelledStream(httpx.SyncByteStream):
            def __iter__(self) -> typing.Iterator[bytes]:
                yield b"Hello"
                raise KeyboardInterrupt()
                yield b", world"  # pragma: no cover

            def close(self) -> None:
                nonlocal stream_was_closed
                stream_was_closed = True

        return httpx.Response(
            200, headers={"Content-Length": "12"}, stream=CancelledStream()
        )

    transport = httpx.MockTransport(response_with_cancel_during_stream)

    with httpx.Client(transport=transport) as client:
        with pytest.raises(KeyboardInterrupt):
            client.get("https://www.example.com")
        assert stream_was_closed


def test_server_extensions(server):
    url = server.url
    with httpx.Client(http2=True) as client:
        response = client.get(url)
    assert response.status_code == 200
    assert response.extensions["http_version"] == b"HTTP/1.1"
