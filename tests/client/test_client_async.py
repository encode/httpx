"""Test the behavior of Client in async environments."""

import threading

import pytest

import httpx

# NOTE: using Client in an async environment is only supported for asyncio, for now.


@pytest.mark.asyncio
async def test_sync_request_in_async_environment(server):
    with httpx.Client() as client:
        response = client.get(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.asyncio
async def test_sync_request_in_async_environment_with_exception(server):
    outer_thread = threading.current_thread()

    class FailingDispatcher(httpx.AsyncDispatcher):
        async def send(self, *args, **kwargs):
            assert threading.current_thread() != outer_thread
            # This shouldn't make the shared sub-thread hang.
            raise ValueError("Failed")

    with pytest.raises(ValueError) as ctx:
        with httpx.Client(dispatch=FailingDispatcher()) as client:
            client.get(server.url)

    exc = ctx.value
    assert isinstance(exc, ValueError)
    assert str(exc) == "Failed"
