import asyncio
import os

import pytest

import httpx
from httpx._utils import (
    ElapsedTimer,
    NetRCInfo,
    get_ca_bundle_from_env,
    get_environment_proxies,
    guess_json_utf,
    obfuscate_sensitive_headers,
    parse_header_links,
    same_origin,
    should_not_be_proxied,
)
from tests.utils import override_log_level

from .common import FIXTURES_DIR, TESTS_DIR


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
    assert guess_json_utf(data) == encoding


def test_bad_utf_like_encoding():
    assert guess_json_utf(b"\x00\x00\x00\x00") is None


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
    assert guess_json_utf(data) == expected


def test_bad_get_netrc_login():
    netrc_info = NetRCInfo([str(FIXTURES_DIR / "does-not-exist")])
    assert netrc_info.get_credentials("netrcexample.org") is None


def test_get_netrc_login():
    netrc_info = NetRCInfo([str(FIXTURES_DIR / ".netrc")])
    expected_credentials = (
        "example-username",
        "example-password",
    )
    assert netrc_info.get_credentials("netrcexample.org") == expected_credentials


def test_get_netrc_unknown():
    netrc_info = NetRCInfo([str(FIXTURES_DIR / ".netrc")])
    assert netrc_info.get_credentials("nonexistant.org") is None


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
    assert parse_header_links(value) == expected


@pytest.mark.asyncio
async def test_logs_debug(server, capsys):
    with override_log_level("debug"):
        async with httpx.AsyncClient() as client:
            response = await client.get(server.url)
            assert response.status_code == 200
    stderr = capsys.readouterr().err
    assert 'HTTP Request: GET http://127.0.0.1:8000/ "HTTP/1.1 200 OK"' in stderr


@pytest.mark.asyncio
async def test_logs_trace(server, capsys):
    with override_log_level("trace"):
        async with httpx.AsyncClient() as client:
            response = await client.get(server.url)
            assert response.status_code == 200
    stderr = capsys.readouterr().err
    assert 'HTTP Request: GET http://127.0.0.1:8000/ "HTTP/1.1 200 OK"' in stderr


@pytest.mark.asyncio
async def test_logs_redirect_chain(server, capsys):
    with override_log_level("debug"):
        async with httpx.AsyncClient() as client:
            response = await client.get(server.url.copy_with(path="/redirect_301"))
            assert response.status_code == 200

    stderr = capsys.readouterr().err.strip()
    redirected_request_line, ok_request_line = stderr.split("\n")
    assert redirected_request_line.endswith(
        "HTTP Request: GET http://127.0.0.1:8000/redirect_301 "
        '"HTTP/1.1 301 Moved Permanently"'
    )
    assert ok_request_line.endswith(
        'HTTP Request: GET http://127.0.0.1:8000/ "HTTP/1.1 200 OK"'
    )


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


@pytest.mark.asyncio
async def test_elapsed_timer():
    with ElapsedTimer() as timer:
        assert timer.elapsed.total_seconds() == pytest.approx(0, abs=0.05)
        await asyncio.sleep(0.1)
    await asyncio.sleep(
        0.1
    )  # test to ensure time spent after timer exits isn't accounted for.
    assert timer.elapsed.total_seconds() == pytest.approx(0.1, abs=0.05)


@pytest.mark.parametrize(
    ["environment", "proxies"],
    [
        ({}, {}),
        ({"HTTP_PROXY": "http://127.0.0.1"}, {"http": "http://127.0.0.1"}),
        (
            {"https_proxy": "http://127.0.0.1", "HTTP_PROXY": "https://127.0.0.1"},
            {"https": "http://127.0.0.1", "http": "https://127.0.0.1"},
        ),
        ({"all_proxy": "http://127.0.0.1"}, {"all": "http://127.0.0.1"}),
        ({"TRAVIS_APT_PROXY": "http://127.0.0.1"}, {}),
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
    bytes_headers = [(k.encode(), v.encode()) for k, v in headers]
    bytes_output = [(k.encode(), v.encode()) for k, v in output]
    assert list(obfuscate_sensitive_headers(headers)) == output
    assert list(obfuscate_sensitive_headers(bytes_headers)) == bytes_output


@pytest.mark.parametrize(
    ["url", "no_proxy", "expected"],
    [
        (
            "http://127.0.0.1",
            {"NO_PROXY": ""},
            False,
        ),  # everything proxied when no_proxy is empty/unset
        (
            "http://127.0.0.1",
            {"NO_PROXY": "127.0.0.1"},
            True,
        ),  # no_proxy as ip case is matched
        (
            "http://127.0.0.1",
            {"NO_PROXY": "https://127.0.0.1"},
            False,
        ),  # no_proxy with scheme is ignored
        (
            "http://127.0.0.1",
            {"NO_PROXY": "1.1.1.1"},
            False,
        ),  # different no_proxy means its proxied
        (
            "http://courses.mit.edu",
            {"NO_PROXY": "mit.edu"},
            True,
        ),  # no_proxy for sub-domain matches
        (
            "https://mit.edu.info",
            {"NO_PROXY": "mit.edu"},
            False,
        ),  # domain is actually edu.info, so should be proxied
        (
            "https://mit.edu.info",
            {"NO_PROXY": "mit.edu,edu.info"},
            True,
        ),  # list in no_proxy, matches second domain
        (
            "https://mit.edu.info",
            {"NO_PROXY": "mit.edu, edu.info"},
            True,
        ),  # list with spaces in no_proxy
        (
            "https://mit.edu.info",
            {"NO_PROXY": "mit.edu,mit.info"},
            False,
        ),  # list in no_proxy, without any domain matching
        (
            "https://foo.example.com",
            {"NO_PROXY": "www.example.com"},
            False,
        ),  # different subdomains foo vs www means we still proxy
        (
            "https://www.example1.com",
            {"NO_PROXY": ".example1.com"},
            True,
        ),  # no_proxy starting with dot
        (
            "https://www.example2.com",
            {"NO_PROXY": "ample2.com"},
            False,
        ),  # whole-domain matching
        (
            "https://www.example3.com",
            {"NO_PROXY": "*"},
            True,
        ),  # wildcard * means nothing proxied
    ],
)
def test_should_not_be_proxied(url, no_proxy, expected):
    os.environ.update(no_proxy)
    parsed_url = httpx.URL(url)
    assert should_not_be_proxied(parsed_url) == expected


def test_same_origin():
    origin1 = httpx.URL("https://example.com")
    origin2 = httpx.URL("HTTPS://EXAMPLE.COM:443")
    assert same_origin(origin1, origin2)


def test_not_same_origin():
    origin1 = httpx.URL("https://example.com")
    origin2 = httpx.URL("HTTP://EXAMPLE.COM")
    assert not same_origin(origin1, origin2)
