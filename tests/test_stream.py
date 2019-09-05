import pytest

from httpx import AsyncioBackend, SSLConfig, TimeoutConfig


@pytest.mark.asyncio
async def test_get_http_version():
    context = SSLConfig().load_ssl_context()
    backend = AsyncioBackend()
    timeout = TimeoutConfig()
    stream = await backend.connect("example.org", 443, context, timeout)
    assert stream.get_http_version() == "HTTP/2"
