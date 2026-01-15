"""
Tests for BoundSyncStream and BoundAsyncStream weakref behavior.
These tests verify that the streams properly break reference cycles
to allow garbage collection.
"""

import gc
import typing
import weakref

import pytest

import httpx
from httpx._client import BoundAsyncStream, BoundSyncStream
from httpx._types import AsyncByteStream, SyncByteStream


class MockSyncStream(SyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        yield b"test"

    def close(self) -> None:
        self.closed = True


class MockAsyncStream(AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b"test"

    async def aclose(self) -> None:
        self.closed = True


def test_bound_sync_stream_sets_elapsed():
    response = httpx.Response(200, content=b"")
    stream = MockSyncStream()
    bound_stream = BoundSyncStream(stream, response=response, start=0.0)
    bound_stream.close()
    assert hasattr(response, "_elapsed")
    assert response.elapsed.total_seconds() >= 0


def test_bound_sync_stream_handles_collected_response():
    response = httpx.Response(200, content=b"")
    stream = MockSyncStream()
    bound_stream = BoundSyncStream(stream, response=response, start=0.0)
    del response
    gc.collect()
    bound_stream.close()
    assert stream.closed


def test_bound_sync_stream_no_reference_cycle():
    response = httpx.Response(200, content=b"")
    response_ref = weakref.ref(response)
    stream = MockSyncStream()
    bound_stream = BoundSyncStream(stream, response=response, start=0.0)
    response.stream = bound_stream
    del response
    gc.collect()
    assert response_ref() is None, "Response should have been garbage collected"


@pytest.mark.anyio
async def test_bound_async_stream_sets_elapsed():
    response = httpx.Response(200, content=b"")
    stream = MockAsyncStream()
    bound_stream = BoundAsyncStream(stream, response=response, start=0.0)
    await bound_stream.aclose()
    assert hasattr(response, "_elapsed")
    assert response.elapsed.total_seconds() >= 0


@pytest.mark.anyio
async def test_bound_async_stream_handles_collected_response():
    response = httpx.Response(200, content=b"")
    stream = MockAsyncStream()
    bound_stream = BoundAsyncStream(stream, response=response, start=0.0)
    del response
    gc.collect()
    await bound_stream.aclose()
    assert stream.closed


@pytest.mark.anyio
async def test_bound_async_stream_no_reference_cycle():
    response = httpx.Response(200, content=b"")
    response_ref = weakref.ref(response)
    stream = MockAsyncStream()
    bound_stream = BoundAsyncStream(stream, response=response, start=0.0)
    response.stream = bound_stream
    del response
    gc.collect()
    assert response_ref() is None, "Response should have been garbage collected"
