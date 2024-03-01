import json
import logging
import os
import random

import certifi
import pytest

import httpx
from httpx._utils import (
    URLPattern,
    get_ca_bundle_from_env,
    get_environment_proxies,
)

from .common import TESTS_DIR


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
    content = '{"abc": 123}'.encode(encoding)
    response = httpx.Response(200, content=content)
    assert response.json() == {"abc": 123}


def test_bad_utf_like_encoding():
    content = b"\x00\x00\x00\x00"
    response = httpx.Response(200, content=content)
    with pytest.raises(json.decoder.JSONDecodeError):
        response.json()


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
    content = '\ufeff{"abc": 123}'.encode(encoding)
    response = httpx.Response(200, content=content)
    assert response.json() == {"abc": 123}


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


def test_parse_header_links_no_link():
    all_links = httpx.Response(200).links
    assert all_links == {}


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
            "HTTP Request: GET http://127.0.0.1:8000/redirect_301"
            ' "HTTP/1.1 301 Moved Permanently"',
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


def test_get_ssl_cert_file():
    # Two environments is not set.
    assert get_ca_bundle_from_env() is None

    os.environ["SSL_CERT_DIR"] = str(TESTS_DIR)
    # SSL_CERT_DIR is correctly set, SSL_CERT_FILE is not set.
    ca_bundle = get_ca_bundle_from_env()
    assert ca_bundle is not None and ca_bundle.endswith("tests")

    del os.environ["SSL_CERT_DIR"]
    os.environ["SSL_CERT_FILE"] = str(TESTS_DIR / "test_utils.py")
    # SSL_CERT_FILE is correctly set, SSL_CERT_DIR is not set.
    ca_bundle = get_ca_bundle_from_env()
    assert ca_bundle is not None and ca_bundle.endswith("tests/test_utils.py")

    os.environ["SSL_CERT_FILE"] = "wrongfile"
    # SSL_CERT_FILE is set with wrong file,  SSL_CERT_DIR is not set.
    assert get_ca_bundle_from_env() is None

    del os.environ["SSL_CERT_FILE"]
    os.environ["SSL_CERT_DIR"] = "wrongpath"
    # SSL_CERT_DIR is set with wrong path,  SSL_CERT_FILE is not set.
    assert get_ca_bundle_from_env() is None

    os.environ["SSL_CERT_DIR"] = str(TESTS_DIR)
    os.environ["SSL_CERT_FILE"] = str(TESTS_DIR / "test_utils.py")
    # Two environments is correctly set.
    ca_bundle = get_ca_bundle_from_env()
    assert ca_bundle is not None and ca_bundle.endswith("tests/test_utils.py")

    os.environ["SSL_CERT_FILE"] = "wrongfile"
    # Two environments is set but SSL_CERT_FILE is not a file.
    ca_bundle = get_ca_bundle_from_env()
    assert ca_bundle is not None and ca_bundle.endswith("tests")

    os.environ["SSL_CERT_DIR"] = "wrongpath"
    # Two environments is set but both are not correct.
    assert get_ca_bundle_from_env() is None


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
        ({"no_proxy": "http://github.com"}, {"http://github.com": None}),
    ],
)
def test_get_environment_proxies(environment, proxies):
    os.environ.update(environment)

    assert get_environment_proxies() == proxies


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
    pattern = URLPattern(pattern)
    assert pattern.matches(httpx.URL(url)) == expected


def test_pattern_priority():
    matchers = [
        URLPattern("all://"),
        URLPattern("http://"),
        URLPattern("http://example.com"),
        URLPattern("http://example.com:123"),
    ]
    random.shuffle(matchers)
    assert sorted(matchers) == [
        URLPattern("http://example.com:123"),
        URLPattern("http://example.com"),
        URLPattern("http://"),
        URLPattern("all://"),
    ]
