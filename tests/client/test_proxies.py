import httpcore
import pytest

import httpx


def url_to_origin(url: str) -> httpcore.URL:
    """
    Given a URL string, return the origin in the raw tuple format that
    `httpcore` uses for it's representation.
    """
    u = httpx.URL(url)
    return httpcore.URL(scheme=u.raw_scheme, host=u.raw_host, port=u.port, target="/")


@pytest.mark.parametrize(
    ["proxy", "expected_proxies"],
    [
        ("http://127.0.0.1", [("all://", "http://127.0.0.1")]),
        (httpx.Proxy("http://127.0.0.1"), [("all://", "http://127.0.0.1")]),
    ],
)
def test_proxy_parameter(proxy, expected_proxies):
    client = httpx.Client(proxy=proxy)
    client_patterns = [p.pattern for p in client._mounts.keys()]
    client_proxies = list(client._mounts.values())

    for proxy_key, url in expected_proxies:
        assert proxy_key in client_patterns
        proxy = client_proxies[client_patterns.index(proxy_key)]
        assert isinstance(proxy, httpx.HTTPTransport)
        assert isinstance(proxy._pool, httpcore.HTTPProxy)
        assert proxy._pool._proxy_url == url_to_origin(url)

    assert len(expected_proxies) == len(client._mounts)


def test_socks_proxy():
    url = httpx.URL("http://www.example.com")

    client = httpx.Client(proxy="socks5://localhost/")
    transport = client._transport_for_url(url)
    assert isinstance(transport, httpx.HTTPTransport)
    assert isinstance(transport._pool, httpcore.SOCKSProxy)

    async_client = httpx.AsyncClient(proxy="socks5://localhost/")
    async_transport = async_client._transport_for_url(url)
    assert isinstance(async_transport, httpx.AsyncHTTPTransport)
    assert isinstance(async_transport._pool, httpcore.AsyncSOCKSProxy)


def test_unsupported_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.Client(proxy="ftp://127.0.0.1")


@pytest.mark.parametrize(
    ["url", "env", "expected"],
    [
        ("http://google.com", {}, None),
        (
            "http://google.com",
            {"HTTP_PROXY": "http://example.com"},
            "http://example.com",
        ),
        # Auto prepend http scheme
        ("http://google.com", {"HTTP_PROXY": "example.com"}, "http://example.com"),
        (
            "http://google.com",
            {"HTTP_PROXY": "http://example.com", "NO_PROXY": "google.com"},
            None,
        ),
        # Everything proxied when NO_PROXY is empty/unset
        (
            "http://127.0.0.1",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": ""},
            "http://localhost:123",
        ),
        # Not proxied if NO_PROXY matches URL.
        (
            "http://127.0.0.1",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "127.0.0.1"},
            None,
        ),
        # Proxied if NO_PROXY scheme does not match URL.
        (
            "http://127.0.0.1",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "https://127.0.0.1"},
            "http://localhost:123",
        ),
        # Proxied if NO_PROXY scheme does not match host.
        (
            "http://127.0.0.1",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "1.1.1.1"},
            "http://localhost:123",
        ),
        # Not proxied if NO_PROXY matches host domain suffix.
        (
            "http://courses.mit.edu",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "mit.edu"},
            None,
        ),
        # Proxied even though NO_PROXY matches host domain *prefix*.
        (
            "https://mit.edu.info",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "mit.edu"},
            "http://localhost:123",
        ),
        # Not proxied if one item in NO_PROXY case matches host domain suffix.
        (
            "https://mit.edu.info",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "mit.edu,edu.info"},
            None,
        ),
        # Not proxied if one item in NO_PROXY case matches host domain suffix.
        # May include whitespace.
        (
            "https://mit.edu.info",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "mit.edu, edu.info"},
            None,
        ),
        # Proxied if no items in NO_PROXY match.
        (
            "https://mit.edu.info",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "mit.edu,mit.info"},
            "http://localhost:123",
        ),
        # Proxied if NO_PROXY domain doesn't match.
        (
            "https://foo.example.com",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "www.example.com"},
            "http://localhost:123",
        ),
        # Not proxied for subdomains matching NO_PROXY, with a leading ".".
        (
            "https://www.example1.com",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": ".example1.com"},
            None,
        ),
        # Proxied, because NO_PROXY subdomains only match if "." separated.
        (
            "https://www.example2.com",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "ample2.com"},
            "http://localhost:123",
        ),
        # No requests are proxied if NO_PROXY="*" is set.
        (
            "https://www.example3.com",
            {"ALL_PROXY": "http://localhost:123", "NO_PROXY": "*"},
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
        assert transport._pool._proxy_url == url_to_origin(expected)


def test_proxy_with_mounts():
    proxy_transport = httpx.HTTPTransport(proxy="http://127.0.0.1")
    client = httpx.Client(mounts={"http://": proxy_transport})

    transport = client._transport_for_url(httpx.URL("http://example.com"))
    assert transport == proxy_transport
