import pytest

import httpx


@pytest.mark.parametrize(
    ["proxies", "expected_proxies"],
    [
        ("http://127.0.0.1", [("all", "http://127.0.0.1")]),
        ({"all": "http://127.0.0.1"}, [("all", "http://127.0.0.1")]),
        (
            {"http": "http://127.0.0.1", "https": "https://127.0.0.1"},
            [("http", "http://127.0.0.1"), ("https", "https://127.0.0.1")],
        ),
        (httpx.HTTPProxy("http://127.0.0.1"), [("all", "http://127.0.0.1")]),
        (
            {"https": httpx.HTTPProxy("https://127.0.0.1"), "all": "http://127.0.0.1"},
            [("all", "http://127.0.0.1"), ("https", "https://127.0.0.1")],
        ),
    ],
)
def test_proxies_parameter(proxies, expected_proxies):
    client = httpx.Client(proxies=proxies)

    for proxy_key, url in expected_proxies:
        assert proxy_key in client.proxies
        assert client.proxies[proxy_key].proxy_url == url

    assert len(expected_proxies) == len(client.proxies)


def test_proxies_has_same_properties_as_dispatch():
    client = httpx.Client(
        proxies="http://127.0.0.1",
        verify="/path/to/verify",
        cert="/path/to/cert",
        trust_env=False,
        timeout=30,
    )
    pool = client.dispatch
    proxy = client.proxies["all"]

    assert isinstance(pool, httpx.ConnectionPool)
    assert isinstance(proxy, httpx.HTTPProxy)

    for prop in [
        "verify",
        "cert",
        "pool_limits",
    ]:
        assert getattr(pool, prop) == getattr(proxy, prop)


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
def test_dispatcher_for_request(url, proxies, expected):
    client = httpx.Client(proxies=proxies)
    dispatcher = client.dispatcher_for_url(httpx.URL(url))

    if expected is None:
        assert isinstance(dispatcher, httpx.ConnectionPool)
        assert dispatcher is client.dispatch
    else:
        assert isinstance(dispatcher, httpx.HTTPProxy)
        assert dispatcher.proxy_url == expected


def test_unsupported_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.Client(proxies="ftp://127.0.0.1")
