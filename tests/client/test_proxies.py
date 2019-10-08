import os

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
    client = httpx.AsyncClient(
        proxies="http://127.0.0.1",
        verify="/path/to/verify",
        cert="/path/to/cert",
        trust_env=False,
        timeout=30,
        http_versions=["HTTP/1.1"],
    )
    pool = client.dispatch
    proxy = client.proxies["all"]

    assert isinstance(pool, httpx.ConnectionPool)
    assert isinstance(proxy, httpx.HTTPProxy)

    for prop in [
        "verify",
        "cert",
        "timeout",
        "pool_limits",
        "http_versions",
        "backend",
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
    client = httpx.AsyncClient(proxies=proxies)
    request = httpx.AsyncRequest("GET", url)
    dispatcher = client._dispatcher_for_request(request, client.proxies)

    if expected is None:
        assert isinstance(dispatcher, httpx.ConnectionPool)
        assert dispatcher is client.dispatch
    else:
        assert isinstance(dispatcher, httpx.HTTPProxy)
        assert dispatcher.proxy_url == expected


def test_unsupported_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.AsyncClient(proxies="ftp://127.0.0.1")


@pytest.mark.parametrize(
    ["passed_in_param", "passed_in_env", "expected_in_client"],
    [
        ("http://127.0.0.1", None, ["http://127.0.0.1"]),
        (None, "http://127.0.0.2", ["http://127.0.0.2"]),
        ("127.0.0.3,1.1.1.1", "http://127.0.0.3", ["127.0.0.3", "1.1.1.1"]),
        (None, "127.0.0.4,1.1.1.1", ["127.0.0.4", "1.1.1.1"]),
    ],
)
def test_no_proxy_parameter(passed_in_param, passed_in_env, expected_in_client):
    "test that no_proxy passed in client takes priority"
    no_proxy = {"NO_PROXY": passed_in_env} if passed_in_env else {}
    os.environ.update(no_proxy)
    client = httpx.Client(no_proxy=passed_in_param)

    for proxy_url in expected_in_client:
        assert proxy_url in client.no_proxy_list

    assert len(expected_in_client) == len(client.no_proxy_list)


@pytest.mark.parametrize(
    ["url", "no_proxy", "proxy", "is_proxied"],
    [
        ("http://127.0.0.1", "127.0.0.1", "http://1.1.1.1", False),
        ("http://127.0.0.1", ",,", "http://1.1.1.1", True),
        ("http://127.0.0.1", "127.0.0.3", "http://1.1.1.1", True),
    ],
)
def test_dispatcher_when_no_proxy_set(url, no_proxy, proxy, is_proxied):
    client = httpx.AsyncClient(proxies=proxy, no_proxy=no_proxy)
    request = httpx.AsyncRequest("GET", url)
    dispatcher = client._dispatcher_for_request(request, client.proxies)

    if not is_proxied:
        assert isinstance(dispatcher, httpx.ConnectionPool)
        assert dispatcher is client.dispatch
    else:
        assert isinstance(dispatcher, httpx.HTTPProxy)
        assert dispatcher.proxy_url == proxy
