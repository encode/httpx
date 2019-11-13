"""Test the behavior of Client in async environments."""

import pytest

import httpx


async def test_sync_request_in_async_environment(server, backend):
    with httpx.Client() as client:
        response = client.get(server.url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


async def test_sync_request_in_async_environment_with_exception(server, backend):
    """Test that inner exceptions surface correctly."""

    class FailingDispatcher(httpx.AsyncDispatcher):
        async def send(self, *args, **kwargs):
            raise ValueError("Failed")

    with pytest.raises(ValueError) as ctx:
        with httpx.Client(dispatch=FailingDispatcher()) as client:
            client.get(server.url)

    exc = ctx.value
    assert isinstance(exc, ValueError)
    assert str(exc) == "Failed"
