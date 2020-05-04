import pytest

import httpcore
import httpx


@pytest.mark.parametrize(
    ["proxies", "expected_proxies"],
    [
        (
            "http://127.0.0.1",
            [("http", "http://127.0.0.1"), ("https", "http://127.0.0.1")],
        ),
        (
            {"all": "http://127.0.0.1"},
            [("http", "http://127.0.0.1"), ("https", "http://127.0.0.1")],
        ),
        (
            {"http": "http://127.0.0.1", "https": "https://127.0.0.1"},
            [("http", "http://127.0.0.1"), ("https", "https://127.0.0.1")],
        ),
        (
            httpx.Proxy("http://127.0.0.1"),
            [("http", "http://127.0.0.1"), ("https", "http://127.0.0.1")],
        ),
        (
            {"https": httpx.Proxy("https://127.0.0.1"), "all": "http://127.0.0.1"},
            [("http", "http://127.0.0.1"), ("https", "https://127.0.0.1")],
        ),
        (
            {
                "https": httpx.Proxy("https://127.0.0.1"),
                "all://example.org": "http://127.0.0.1:8080",
            },
            [
                ("https", "https://127.0.0.1"),
                ("http://example.org", "http://127.0.0.1:8080"),
                ("https://example.org", "http://127.0.0.1:8080"),
            ],
        ),
    ],
)
def test_proxies_parameter(proxies, expected_proxies):
    client = httpx.AsyncClient(proxies=proxies)

    for proxy_key, url in expected_proxies:
        assert proxy_key in client.proxies
        assert client.proxies[proxy_key].proxy_origin == httpx.URL(url).raw[:3]

    assert len(expected_proxies) == len(client.proxies)


@pytest.mark.parametrize("proxies", [{"https": 42}, httpcore.AsyncHTTPTransport()])
def test_invalid_proxy_parameter(proxies):
    with pytest.raises(RuntimeError):
        httpx.AsyncClient(proxies=proxies)


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
    transport = client.transport_for_url(httpx.URL(url))

    if expected is None:
        assert transport is client.transport
    else:
        assert transport.proxy_origin == httpx.URL(expected).raw[:3]


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
def test_proxies_environ(monkeypatch, url, env, expected):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    client = httpx.AsyncClient()
    transport = client.transport_for_url(httpx.URL(url))

    if expected is None:
        assert transport == client.transport
    else:
        assert transport.proxy_origin == httpx.URL(expected).raw[:3]
