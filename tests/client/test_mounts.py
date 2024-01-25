import pytest

import httpx


def mounted_at_http(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="Mounted at 'http://'")


def mounted_at_https(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="Mounted at 'https://'")


def test_mounts():
    """
    The `httpx.Mounts` transport class should route requests correctly.
    """
    transport = httpx.Mounts(
        {
            "http://": httpx.MockTransport(mounted_at_http),
            "https://": httpx.MockTransport(mounted_at_https),
        }
    )
    with httpx.Client(transport=transport) as client:
        response = client.get("http://www.example.com")
        assert response.text == "Mounted at 'http://'"
        response = client.get("https://www.example.com")
        assert response.text == "Mounted at 'https://'"


def test_unmounted_pattern_raises_exception():
    """
    The `httpx.Mounts` transport class should raise an exception
    if it cannot route a request.
    """
    transport = httpx.Mounts(
        {
            "http://": httpx.MockTransport(mounted_at_http),
            "https://": httpx.MockTransport(mounted_at_https),
        }
    )
    with httpx.Client(transport=transport) as client:
        with pytest.raises(httpx.MountNotFound):
            client.get("other://example.com")


def test_mounts_property():
    """
    The `httpx.Mounts` class should exposes a `.mounts` property.
    """
    transport = httpx.Mounts(
        {
            "http://": httpx.MockTransport(mounted_at_http),
            "https://": httpx.MockTransport(mounted_at_https),
        }
    )
    assert transport.mounts == {
        "http://": httpx.MockTransport(mounted_at_http),
        "https://": httpx.MockTransport(mounted_at_https),
    }


@pytest.mark.anyio
async def test_async_mounts():
    """
    The `httpx.AsyncMounts` transport class should route requests correctly.
    """
    mounts = httpx.AsyncMounts(
        {
            "http://": httpx.MockTransport(mounted_at_http),
            "https://": httpx.MockTransport(mounted_at_https),
        }
    )
    async with httpx.AsyncClient(transport=mounts) as client:
        response = await client.get("http://www.example.com")
        assert response.text == "Mounted at 'http://'"
        response = await client.get("https://www.example.com")
        assert response.text == "Mounted at 'https://'"
        with pytest.raises(httpx.MountNotFound):
            await client.get("other://example.com")


@pytest.mark.anyio
async def test_async_unmounted_pattern_raises_exception():
    """
    The `httpx.AsyncMounts` transport class should raise an exception
    if it cannot route a request.
    """
    transport = httpx.AsyncMounts(
        {
            "http://": httpx.MockTransport(mounted_at_http),
            "https://": httpx.MockTransport(mounted_at_https),
        }
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.MountNotFound):
            await client.get("other://example.com")


@pytest.mark.anyio
async def test_async_mounts_property():
    """
    The `httpx.AsyncMounts` class should expose a `.mounts` property.
    """
    transport = httpx.AsyncMounts(
        {
            "http://": httpx.MockTransport(mounted_at_http),
            "https://": httpx.MockTransport(mounted_at_https),
        }
    )
    assert transport.mounts == {
        "http://": httpx.MockTransport(mounted_at_http),
        "https://": httpx.MockTransport(mounted_at_https),
    }
