from __future__ import annotations

from datetime import timedelta

import pytest

import httpx


class PreloadedTransport(httpx.BaseTransport):
    """A transport that answers with an already-loaded body, like a cache would."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"ok", request=request)


class PreloadedAsyncTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"ok", request=request)


def test_mock_transport_sets_elapsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Hello, world!")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.org")

    assert isinstance(response.elapsed, timedelta)
    assert response.elapsed >= timedelta()


def test_preloaded_response_sets_elapsed() -> None:
    """`Response.close()` returns early on an already-closed response, so the
    bound stream that normally records `.elapsed` is never closed."""
    with httpx.Client(transport=PreloadedTransport()) as client:
        response = client.get("http://example.org/")

    assert response.is_closed
    assert isinstance(response.elapsed, timedelta)
    assert response.elapsed >= timedelta()


def test_preloaded_response_stream_sets_elapsed() -> None:
    with httpx.Client(transport=PreloadedTransport()) as client:
        with client.stream("GET", "http://example.org/") as response:
            assert isinstance(response.elapsed, timedelta)


def test_handler_elapsed_is_preserved() -> None:
    elapsed = timedelta(seconds=2)

    def handler(request: httpx.Request) -> httpx.Response:
        response = httpx.Response(200, text="Hello, world!")
        response.elapsed = elapsed
        return response

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.org")

    assert response.elapsed == elapsed


def test_streaming_transport_still_sets_elapsed_on_close() -> None:
    """The wrapping path must keep working for transports with a live stream."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=httpx.ByteStream(b"ok"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.org")

    assert not response.is_closed or response.is_stream_consumed
    assert isinstance(response.elapsed, timedelta)


@pytest.mark.anyio
async def test_async_mock_transport_sets_elapsed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Hello, world!")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://example.org")

    assert isinstance(response.elapsed, timedelta)
    assert response.elapsed >= timedelta()


@pytest.mark.anyio
async def test_async_preloaded_response_sets_elapsed() -> None:
    async with httpx.AsyncClient(transport=PreloadedAsyncTransport()) as client:
        response = await client.get("http://example.org/")

    assert response.is_closed
    assert isinstance(response.elapsed, timedelta)
    assert response.elapsed >= timedelta()


@pytest.mark.anyio
async def test_async_preloaded_response_stream_sets_elapsed() -> None:
    async with httpx.AsyncClient(transport=PreloadedAsyncTransport()) as client:
        async with client.stream("GET", "http://example.org/") as response:
            assert isinstance(response.elapsed, timedelta)


@pytest.mark.anyio
async def test_async_handler_elapsed_is_preserved() -> None:
    elapsed = timedelta(seconds=2)

    async def handler(request: httpx.Request) -> httpx.Response:
        response = httpx.Response(200, text="ok")
        response.elapsed = elapsed
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await client.get("http://example.org")

    assert response.elapsed == elapsed
