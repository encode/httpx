import httpcore
import pytest

import httpx


def url_to_origin(url: str):
    """
    Given a URL string, return the origin in the raw tuple format that
    `httpcore` uses for it's representation.
    """
    DEFAULT_PORTS = {b"http": 80, b"https": 443}
    scheme, host, explicit_port = httpx.URL(url).raw[:3]
    default_port = DEFAULT_PORTS[scheme]
    port = default_port if explicit_port is None else explicit_port
    return scheme, host, port


@pytest.mark.parametrize(
    ["proxies", "expected_proxies"],
    [
        ("http://127.0.0.1", [("all", "http://127.0.0.1")]),
        ({"all": "http://127.0.0.1"}, [("all", "http://127.0.0.1")]),
        (
            {"http": "http://127.0.0.1", "https": "https://127.0.0.1"},
            [("http", "http://127.0.0.1"), ("https", "https://127.0.0.1")],
        ),
        (httpx.Proxy("http://127.0.0.1"), [("all", "http://127.0.0.1")]),
        (
            {"https": httpx.Proxy("https://127.0.0.1"), "all": "http://127.0.0.1"},
            [("all", "http://127.0.0.1"), ("https", "https://127.0.0.1")],
        ),
    ],
)
def test_proxies_parameter(proxies, expected_proxies):
    client = httpx.AsyncClient(proxies=proxies)

    for proxy_key, url in expected_proxies:
        assert proxy_key in client._proxies
        proxy = client._proxies[proxy_key]
        assert isinstance(proxy, httpcore.AsyncHTTPProxy)
        assert proxy.proxy_origin == url_to_origin(url)

    assert len(expected_proxies) == len(client._proxies)


PROXY_URL = "http://[::1]"


@pytest.mark.parametrize(
    ["url", "proxies", "expected"],
    [
        ("http://example.com", None, None),
        ("http://example.com", {}, None),
        ("http://example.com", {"https": PROXY_URL}, None),
        ("http://example.com", {"http://example.net": PROXY_URL}, None),
        ("http://example.com:443", {"http://example.com": PROXY_URL}, None),
        ("http://example.com", {"all": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"http": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://example.com:80": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"http://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"http://example.com:80": PROXY_URL}, PROXY_URL),
        ("http://example.com:8080", {"http://example.com:8080": PROXY_URL}, PROXY_URL),
        ("http://example.com:8080", {"http://example.com": PROXY_URL}, None),
        (
            "http://example.com",
            {
                "all": PROXY_URL + ":1",
                "http": PROXY_URL + ":2",
                "all://example.com": PROXY_URL + ":3",
                "http://example.com": PROXY_URL + ":4",
            },
            PROXY_URL + ":4",
        ),
        (
            "http://example.com",
            {
                "all": PROXY_URL + ":1",
                "http": PROXY_URL + ":2",
                "all://example.com": PROXY_URL + ":3",
            },
            PROXY_URL + ":3",
        ),
        (
            "http://example.com",
            {"all": PROXY_URL + ":1", "http": PROXY_URL + ":2"},
            PROXY_URL + ":2",
        ),
    ],
)
def test_transport_for_request(url, proxies, expected):
    client = httpx.AsyncClient(proxies=proxies)
    transport = client._transport_for_url(httpx.URL(url))

    if expected is None:
        assert transport is client._transport
    else:
        assert isinstance(transport, httpcore.AsyncHTTPProxy)
        assert transport.proxy_origin == url_to_origin(expected)


@pytest.mark.asyncio
async def test_async_proxy_close():
    client = httpx.AsyncClient(proxies={"all": PROXY_URL})
    await client.aclose()


def test_sync_proxy_close():
    client = httpx.Client(proxies={"all": PROXY_URL})
    client.close()


def test_unsupported_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.AsyncClient(proxies="ftp://127.0.0.1")


@pytest.mark.parametrize(
    ["url", "env", "expected"],
    [
        ("http://google.com", {}, None),
        (
            "http://google.com",
            {"HTTP_PROXY": "http://example.com"},
            "http://example.com",
        ),
        (
            "http://google.com",
            {"HTTP_PROXY": "http://example.com", "NO_PROXY": "google.com"},
            None,
        ),
    ],
)
@pytest.mark.parametrize("client_class", [httpx.Client, httpx.AsyncClient])
def test_proxies_environ(monkeypatch, client_class, url, env, expected):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    client = client_class()
    transport = client._transport_for_url(httpx.URL(url))

    if expected is None:
        assert transport == client._transport
    else:
        assert transport.proxy_origin == url_to_origin(expected)
