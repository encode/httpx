import pytest

import httpx


def matched(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="Matched")


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


@pytest.mark.parametrize(
    ["mount_url", "request_url", "should_match"],
    [
        ("http://example.com", "http://example.com", True),
        ("http://example.com", "https://example.com", False),
        ("http://example.com", "http://other.com", False),
        ("http://example.com:123", "http://example.com:123", True),
        ("http://example.com:123", "http://example.com:456", False),
        ("http://example.com:123", "http://example.com", False),
        ("http://*.example.com", "http://www.example.com", True),
        ("http://*.example.com", "http://example.com", False),
        ("http://*example.com", "http://www.example.com", True),
        ("http://*example.com", "http://example.com", True),
        ("all://example.com", "http://example.com", True),
        ("all://example.com", "https://example.com", True),
        ("http://", "http://example.com", True),
        ("http://", "https://example.com", False),
        ("all://", "https://example.com:123", True),
        ("", "https://example.com:123", True),
    ],
)
def test_url_matches(mount_url, request_url, should_match):
    transport = httpx.Mounts(
        {
            mount_url: httpx.MockTransport(matched),
        }
    )
    with httpx.Client(transport=transport) as client:
        if should_match:
            response = client.get(request_url)
            assert response.text == "Matched"
        else:
            with pytest.raises(httpx.MountNotFound):
                client.get(request_url)


# def test_pattern_priority():
#     matchers = [
#         URLPattern("all://"),
#         URLPattern("http://"),
#         URLPattern("http://example.com"),
#         URLPattern("http://example.com:123"),
#     ]
#     random.shuffle(matchers)
#     assert sorted(matchers) == [
#         URLPattern("http://example.com:123"),
#         URLPattern("http://example.com"),
#         URLPattern("http://"),
#         URLPattern("all://"),
#     ]
