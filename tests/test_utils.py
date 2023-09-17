import logging
import os
import random

import certifi
import httpcore
import pytest

import httpx


@pytest.mark.parametrize(
    "encoding",
    (
        "utf-32",
        "utf-8-sig",
        "utf-16",
        "utf-8",
        "utf-16-be",
        "utf-16-le",
        "utf-32-be",
        "utf-32-le",
    ),
)
def test_encoded(encoding):
    data = "{}".encode(encoding)
    response = httpx.Response(200, content=data)
    assert response._guess_content_json_utf() == encoding


def test_bad_utf_like_encoding():
    response = httpx.Response(200, content=b"\x00\x00\x00\x00")
    assert response._guess_content_json_utf() is None


@pytest.mark.parametrize(
    ("encoding", "expected"),
    (
        ("utf-16-be", "utf-16"),
        ("utf-16-le", "utf-16"),
        ("utf-32-be", "utf-32"),
        ("utf-32-le", "utf-32"),
    ),
)
def test_guess_by_bom(encoding, expected):
    data = "\ufeff{}".encode(encoding)
    response = httpx.Response(200, content=data)
    assert response._guess_content_json_utf() == expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (
            '<http:/.../front.jpeg>; rel=front; type="image/jpeg"',
            [{"url": "http:/.../front.jpeg", "rel": "front", "type": "image/jpeg"}],
        ),
        ("<http:/.../front.jpeg>", [{"url": "http:/.../front.jpeg"}]),
        ("<http:/.../front.jpeg>;", [{"url": "http:/.../front.jpeg"}]),
        (
            '<http:/.../front.jpeg>; type="image/jpeg",<http://.../back.jpeg>;',
            [
                {"url": "http:/.../front.jpeg", "type": "image/jpeg"},
                {"url": "http://.../back.jpeg"},
            ],
        ),
        ("", []),
    ),
)
def test_parse_header_links(value, expected):
    all_links = httpx.Response(200, headers={"link": value}).links.values()
    assert all(link in all_links for link in expected)


def test_logging_request(server, caplog):
    caplog.set_level(logging.INFO)
    with httpx.Client() as client:
        response = client.get(server.url)
        assert response.status_code == 200

    assert caplog.record_tuples == [
        (
            "httpx",
            logging.INFO,
            'HTTP Request: GET http://127.0.0.1:8000/ "HTTP/1.1 200 OK"',
        )
    ]


def test_logging_redirect_chain(server, caplog):
    caplog.set_level(logging.INFO)
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(server.url.copy_with(path="/redirect_301"))
        assert response.status_code == 200

    assert caplog.record_tuples == [
        (
            "httpx",
            logging.INFO,
            'HTTP Request: GET http://127.0.0.1:8000/redirect_301 "HTTP/1.1 301 Moved Permanently"',
        ),
        (
            "httpx",
            logging.INFO,
            'HTTP Request: GET http://127.0.0.1:8000/ "HTTP/1.1 200 OK"',
        ),
    ]


def test_logging_ssl(caplog):
    caplog.set_level(logging.DEBUG)
    with httpx.Client():
        pass

    cafile = certifi.where()
    assert caplog.record_tuples == [
        (
            "httpx",
            logging.DEBUG,
            "load_ssl_context verify=True cert=None trust_env=True http2=False",
        ),
        (
            "httpx",
            logging.DEBUG,
            f"load_verify_locations cafile='{cafile}'",
        ),
    ]


@pytest.mark.parametrize(
    ["environment", "proxies"],
    [
        ({}, {}),
        ({"HTTP_PROXY": "http://127.0.0.1"}, {"http://": "http://127.0.0.1"}),
        (
            {"https_proxy": "http://127.0.0.1", "HTTP_PROXY": "https://127.0.0.1"},
            {"https://": "http://127.0.0.1", "http://": "https://127.0.0.1"},
        ),
        ({"all_proxy": "http://127.0.0.1"}, {"all://": "http://127.0.0.1"}),
        ({"TRAVIS_APT_PROXY": "http://127.0.0.1"}, {}),
        ({"no_proxy": "127.0.0.1"}, {"all://127.0.0.1": None}),
        ({"no_proxy": "192.168.0.0/16"}, {"all://192.168.0.0/16": None}),
        ({"no_proxy": "::1"}, {"all://[::1]": None}),
        ({"no_proxy": "localhost"}, {"all://localhost": None}),
        ({"no_proxy": "github.com"}, {"all://*github.com": None}),
        ({"no_proxy": ".github.com"}, {"all://*.github.com": None}),
    ],
)
def test_get_environment_proxies(environment, proxies):
    as_classes = {
        pattern: None if proxy is None else httpx.Proxy(url=proxy)
        for pattern, proxy in proxies.items()
    }

    os.environ.update(environment)
    client = httpx.Client()

    for pat, transport in client._mounts.items():
        expected = as_classes[pat.pattern]
        if transport is None:
            assert expected is None
        else:
            assert expected is not None

            assert isinstance(transport, httpx.HTTPTransport)
            assert isinstance(
                transport._pool, (httpcore.HTTPProxy, httpcore.SOCKSProxy)
            )
            proxy_url = transport._pool._proxy_url

            assert proxy_url.scheme == expected.url.raw_scheme
            assert proxy_url.host == expected.url.raw_host
            assert proxy_url.port == expected.url.port
            assert proxy_url.target == expected.url.raw_path


@pytest.mark.parametrize(
    "headers, output",
    [
        ([("content-type", "text/html")], [("content-type", "text/html")]),
        ([("authorization", "s3kr3t")], [("authorization", "[secure]")]),
        ([("proxy-authorization", "s3kr3t")], [("proxy-authorization", "[secure]")]),
    ],
)
def test_obfuscate_sensitive_headers(headers, output):
    as_dict = {k: v for k, v in output}
    headers_class = httpx.Headers({k: v for k, v in headers})
    assert repr(headers_class) == f"Headers({as_dict!r})"


def test_same_origin():
    origin = httpx.URL("https://example.com")
    request = httpx.Request("GET", "HTTPS://EXAMPLE.COM:443")

    client = httpx.Client()
    headers = client._redirect_headers(request, origin, "GET")

    assert headers["Host"] == request.url.netloc.decode("ascii")


def test_not_same_origin():
    origin = httpx.URL("https://example.com")
    request = httpx.Request("GET", "HTTP://EXAMPLE.COM:80")

    client = httpx.Client()
    headers = client._redirect_headers(request, origin, "GET")

    assert headers["Host"] == origin.netloc.decode("ascii")


def test_is_https_redirect():
    url = httpx.URL("https://example.com")
    request = httpx.Request(
        "GET", "http://example.com", headers={"Authorization": "empty"}
    )

    client = httpx.Client()
    headers = client._redirect_headers(request, url, "GET")

    assert "Authorization" in headers


def test_is_not_https_redirect():
    url = httpx.URL("https://www.example.com")
    request = httpx.Request(
        "GET", "http://example.com", headers={"Authorization": "empty"}
    )

    client = httpx.Client()
    headers = client._redirect_headers(request, url, "GET")

    assert "Authorization" not in headers


def test_is_not_https_redirect_if_not_default_ports():
    url = httpx.URL("https://example.com:1337")
    request = httpx.Request(
        "GET", "http://example.com:9999", headers={"Authorization": "empty"}
    )

    client = httpx.Client()
    headers = client._redirect_headers(request, url, "GET")

    assert "Authorization" not in headers


@pytest.mark.parametrize(
    ["pattern", "url", "expected"],
    [
        ("http://example.com", "http://example.com", True),
        ("http://example.com", "https://example.com", False),
        ("http://example.com", "http://other.com", False),
        ("http://example.com:123", "http://example.com:123", True),
        ("http://example.com:123", "http://example.com:456", False),
        ("http://example.com:123", "http://example.com", False),
        ("all://example.com", "http://example.com", True),
        ("all://example.com", "https://example.com", True),
        ("http://", "http://example.com", True),
        ("http://", "https://example.com", False),
        ("all://", "https://example.com:123", True),
        ("", "https://example.com:123", True),
    ],
)
def test_url_matches(pattern, url, expected):
    client = httpx.Client(mounts={pattern: httpx.BaseTransport()})
    pattern = next(iter(client._mounts))
    assert pattern.matches(httpx.URL(url)) == expected


def test_pattern_priority():
    matchers = [
        "all://",
        "http://",
        "http://example.com",
        "http://example.com:123",
    ]
    random.shuffle(matchers)

    transport = httpx.BaseTransport()
    client = httpx.Client(mounts={m: transport for m in matchers})

    assert [pat.pattern for pat in client._mounts] == [
        "http://example.com:123",
        "http://example.com",
        "http://",
        "all://",
    ]
