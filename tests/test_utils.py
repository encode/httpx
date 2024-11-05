import json
import logging

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
