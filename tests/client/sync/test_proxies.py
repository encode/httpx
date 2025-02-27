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



def test_socks_proxy():
    url = httpx.URL("http://www.example.com")

    for proxy in ("socks5://localhost/", "socks5h://localhost/"):
        with httpx.Client(proxy=proxy) as client:
            transport = client._transport_for_url(url)
            assert isinstance(transport, httpx.HTTPTransport)
            assert isinstance(transport._pool, httpcore.SOCKSProxy)


PROXY_URL = "http://[::1]"


@pytest.mark.parametrize(
    ["url", "proxies", "expected"],
    [
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
        ("http://example.com", {"http://": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"all://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"http://example.com": PROXY_URL}, PROXY_URL),
        ("http://example.com", {"http://example.com:80": PROXY_URL}, PROXY_URL),
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
    mounts = {
        key: httpx.HTTPTransport(proxy=value) for key, value in proxies.items()
    }
    with httpx.Client(mounts=mounts) as client:
        transport = client._transport_for_url(httpx.URL(url))

        if expected is None:
            assert transport is client._transport
        else:
            assert isinstance(transport, httpx.HTTPTransport)
            assert isinstance(transport._pool, httpcore.HTTPProxy)
            assert transport._pool._proxy_url == url_to_origin(expected)



@pytest.mark.network
def test_proxy_close():
    try:
        transport = httpx.HTTPTransport(proxy=PROXY_URL)
        client = httpx.Client(mounts={"https://": transport})
        client.get("http://example.com")
    finally:
        client.close()



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

def test_proxies_environ(monkeypatch, url, env, expected):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    with httpx.Client() as client:
        transport = client._transport_for_url(httpx.URL(url))

        if expected is None:
            assert transport == client._transport
        else:
            assert transport._pool._proxy_url == url_to_origin(expected)  # type: ignore


@pytest.mark.parametrize(
    ["proxies", "is_valid"],
    [
        ({"http": "http://127.0.0.1"}, False),
        ({"https": "http://127.0.0.1"}, False),
        ({"all": "http://127.0.0.1"}, False),
        ({"http://": "http://127.0.0.1"}, True),
        ({"https://": "http://127.0.0.1"}, True),
        ({"all://": "http://127.0.0.1"}, True),
    ],
)

def test_for_deprecated_proxy_params(proxies, is_valid):
    mounts = {
        key: httpx.HTTPTransport(proxy=value) for key, value in proxies.items()
    }

    if not is_valid:
        with pytest.raises(ValueError):
            httpx.Client(mounts=mounts)
    else:
        httpx.Client(mounts=mounts)



def test_proxy_with_mounts():
    proxy_transport = httpx.HTTPTransport(proxy="http://127.0.0.1")

    with httpx.Client(mounts={"http://": proxy_transport}) as client:
        transport = client._transport_for_url(httpx.URL("http://example.com"))
        assert transport == proxy_transport
