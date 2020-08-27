import httpcore
import pytest

import httpx
from httpx._utils import URLPattern


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
        ("http://127.0.0.1", [("all://", "http://127.0.0.1")]),
        ({"all://": "http://127.0.0.1"}, [("all://", "http://127.0.0.1")]),
        (
            {"http://": "http://127.0.0.1", "https://": "https://127.0.0.1"},
            [("http://", "http://127.0.0.1"), ("https://", "https://127.0.0.1")],
        ),
        (httpx.Proxy("http://127.0.0.1"), [("all://", "http://127.0.0.1")]),
        (
            {
                "https://": httpx.Proxy("https://127.0.0.1"),
                "all://": "http://127.0.0.1",
            },
            [("all://", "http://127.0.0.1"), ("https://", "https://127.0.0.1")],
        ),
    ],
)
def test_proxies_parameter(proxies, expected_proxies):
    client = httpx.Client(proxies=proxies)

    for proxy_key, url in expected_proxies:
        pattern = URLPattern(proxy_key)
        assert pattern in client._proxies
        proxy = client._proxies[pattern]
        assert isinstance(proxy, httpcore.SyncHTTPProxy)
        assert proxy.proxy_origin == url_to_origin(url)

    assert len(expected_proxies) == len(client._proxies)


PROXY_URL = "http://[::1]"


@pytest.mark.parametrize(
    ["url", "proxies", "expected"],
    [
        ("http://example.com", None, None),
        ("http://example.com", {}, None),
        ("http://example.com", {"https://": PROXY_URL}, None),
        ("http://example.com", {"http://example.net": PROXY_URL}, None),
        # Using "*" should match any domain name.
        ("http://example.com", {"http://*": PROXY_URL}, PROXY_URL),
        ("https://example.com", {"http://*": PROXY_URL}, None),
        # Using "example.com" should match example.com, but not www.example.com
        ("http://example.com", {"http://example.com": PROXY_URL}, PROXY_URL),
        ("http://www.example.com", {"http://example.com": PROXY_URL}, None),
        # Using "*.example.com" should match www.example.com, but not example.com
        ("http://example.com", {"http://*.example.com": PROXY_URL}, None),
        ("http://www.example.com", {"http://*.example.com": PROXY_URL}, PROXY_URL),
        # Using "*example.com" should match example.com and www.example.com
        ("http://example.com", {"http://*example.com": PROXY_URL}, PROXY_URL),
        ("http://www.example.com", {"http://*example.com": PROXY_URL}, PROXY_URL),
        ("http://wwwexample.com", {"http://*example.com": PROXY_URL}, None),
        # ...
        ("http://example.com:443", {"http://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://": PROXY_URL, "http://example.com": None}, None),
        ("http://example.com", {"http://": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://example.com:80": PROXY_URL}, None),
        ("http://example.com", {"http://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"http://example.com:80": PROXY_URL}, None),
        ("http://example.com:8080", {"http://example.com:8080": PROXY_URL}, PROXY_URL),
        ("http://example.com:8080", {"http://example.com": PROXY_URL}, PROXY_URL),
        (
            "http://example.com",
            {
                "all://": PROXY_URL + ":1",
                "http://": PROXY_URL + ":2",
                "all://example.com": PROXY_URL + ":3",
                "http://example.com": PROXY_URL + ":4",
            },
            PROXY_URL + ":4",
        ),
        (
            "http://example.com",
            {
                "all://": PROXY_URL + ":1",
                "http://": PROXY_URL + ":2",
                "all://example.com": PROXY_URL + ":3",
            },
            PROXY_URL + ":3",
        ),
        (
            "http://example.com",
            {"all://": PROXY_URL + ":1", "http://": PROXY_URL + ":2"},
            PROXY_URL + ":2",
        ),
    ],
)
def test_transport_for_request(url, proxies, expected):
    client = httpx.Client(proxies=proxies)
    transport = client._transport_for_url(httpx.URL(url))

    if expected is None:
        assert transport is client._transport
    else:
        assert isinstance(transport, httpcore.SyncHTTPProxy)
        assert transport.proxy_origin == url_to_origin(expected)


@pytest.mark.asyncio
async def test_async_proxy_close():
    try:
        client = httpx.AsyncClient(proxies={"all://": PROXY_URL})
    finally:
        await client.aclose()


def test_sync_proxy_close():
    try:
        client = httpx.Client(proxies={"all://": PROXY_URL})
    finally:
        client.close()


def test_unsupported_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.Client(proxies="ftp://127.0.0.1")


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
        # Proxied, because NO_PROXY subdomains only match if "." seperated.
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
        assert transport.proxy_origin == url_to_origin(expected)


@pytest.mark.parametrize(
    ["proxies", "expected_scheme"],
    [
        ({"http": "http://127.0.0.1"}, "http://"),
        ({"https": "http://127.0.0.1"}, "https://"),
        ({"all": "http://127.0.0.1"}, "all://"),
    ],
)
def test_for_deprecated_proxy_params(proxies, expected_scheme):
    with pytest.deprecated_call() as block:
        httpx.Client(proxies=proxies)

    warning_message = str(block.pop(DeprecationWarning))

    assert expected_scheme in warning_message
