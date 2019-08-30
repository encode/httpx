"""Tests for asserting the compatibility between HTTPX and Requests."""
# flake8: noqa

from __future__ import division

import collections
import contextlib
import io
import json
import os
import pickle
import socket
import ssl
import warnings
from urllib.parse import urlparse
import pytest

import httpx as requests
from httpx.middleware import build_basic_auth_header
from httpx.exceptions import InvalidURL, TooManyRedirects

# Requests compat
from http import cookiejar as cookielib  # Py3

# HTTPX patches
MissingSchema = InvalidURL
InvalidSchema = InvalidURL
requests.session = requests.Client
requests.Session = requests.Client

# Requests to this URL should always fail with a connection timeout (nothing
# listening on that port)
TARPIT = "http://10.255.255.1"

try:
    from ssl import SSLContext

    del SSLContext
    HAS_MODERN_SSL = True
except ImportError:
    HAS_MODERN_SSL = False

try:
    requests.pyopenssl
    HAS_PYOPENSSL = True
except AttributeError:
    HAS_PYOPENSSL = False


class TestRequests:

    digest_auth_algo = ("MD5", "SHA-256", "SHA-512")

    def test_entry_points(self):
        requests.session
        requests.session().get
        requests.session().head
        requests.get
        requests.head
        requests.put
        requests.patch
        requests.post

    @pytest.mark.parametrize(
        "exception, url",
        (
            (MissingSchema, "hiwpefhipowhefopw"),
            (InvalidSchema, "localhost:3128"),
            (InvalidSchema, "localhost.localdomain:3128/"),
            (InvalidSchema, "10.122.1.1:3128/"),
            (InvalidURL, "http://"),
        ),
    )
    def test_invalid_url(self, exception, url):
        with pytest.raises(exception):
            requests.get(url)

    @pytest.mark.skip("httpx prepares requests by default")
    def test_basic_building(self):
        req = requests.Request()
        req.url = "http://kennethreitz.org/"
        req.data = {"life": "42"}

        pr = req.prepare()
        assert pr.url == req.url
        assert pr.body == "life=42"

    @pytest.mark.parametrize("method", ("GET", "HEAD"))
    def test_no_content_length(self, httpbin, method):
        req = requests.Request(method, httpbin(method.lower()))
        assert "Content-Length" not in req.headers

    @pytest.mark.parametrize("method", ("POST", "PUT", "PATCH", "OPTIONS"))
    def test_no_body_content_length(self, httpbin, method):
        req = requests.Request(method, httpbin(method.lower()))
        assert "content-length" not in req.headers

    @pytest.mark.parametrize("method", ("POST", "PUT", "PATCH", "OPTIONS"))
    def test_empty_content_length(self, httpbin, method):
        req = requests.Request(method, httpbin(method.lower()), data="")
        assert "content-length" not in req.headers

    def test_override_content_length(self, httpbin):
        headers = {"Content-Length": "not zero"}
        r = requests.Request("POST", httpbin("post"), headers=headers)
        assert "Content-Length" in r.headers
        assert r.headers["Content-Length"] == "not zero"

    def test_path_is_not_double_encoded(self):
        request = requests.Request("GET", "http://0.0.0.0/get/test case")
        assert request.url.path == "/get/test%20case"

    @pytest.mark.parametrize(
        "url, expected",
        (
            (
                "http://example.com/path#fragment",
                "http://example.com/path?a=b#fragment",
            ),
            pytest.param(
                "http://example.com/path?key=value#fragment",
                "http://example.com/path?key=value&a=b#fragment",
                marks=[
                    pytest.mark.xfail(
                        reason="existing param ('?key=value') aren't included"
                    ),
                    pytest.mark.httpx_bug,
                ],
            ),
        ),
    )
    def test_params_are_added_before_fragment(self, url, expected):
        request = requests.Request("GET", url, params={"a": "b"})
        assert request.url == expected

    def test_params_original_order_is_preserved_by_default(self):
        param_ordered_dict = collections.OrderedDict(
            (("z", 1), ("a", 1), ("k", 1), ("d", 1))
        )
        request = requests.Request(
            "GET", "http://example.com/", params=param_ordered_dict
        )
        assert request.url == "http://example.com/?z=1&a=1&k=1&d=1"

    @pytest.mark.xfail(reason="HTTPX doesn't support bytes-typed 'params' yet")
    def test_params_bytes_are_encoded(self):
        request = requests.Request("GET", "http://example.com", params=b"test=foo")
        assert request.url == "http://example.com/?test=foo"

    def test_binary_put(self):
        request = requests.Request(
            "PUT", "http://example.com", data="ööö".encode("utf-8")
        )
        assert isinstance(request.content, bytes)

    @pytest.mark.xfail(reason="Not supported by HTTPX yet", raises=InvalidURL)
    def test_whitespaces_are_removed_from_url(self):
        # Test for issue #3696
        request = requests.Request("GET", " http://example.com")
        assert request.url == "http://example.com/"

    @pytest.mark.parametrize("scheme", ("http://", "HTTP://", "hTTp://", "HttP://"))
    def test_mixed_case_scheme_acceptable(self, httpbin, scheme):
        s = requests.Session()
        parts = urlparse(httpbin("get"))
        url = scheme + parts.netloc + parts.path
        r = s.request("GET", url)
        assert r.status_code == 200, "failed for scheme {}".format(scheme)

    def test_HTTP_200_OK_GET_ALTERNATIVE(self, httpbin):
        s = requests.Session()
        r = s.request("GET", httpbin("get"))
        assert r.status_code == 200

    def test_HTTP_302_ALLOW_REDIRECT_GET(self, httpbin):
        r = requests.get(httpbin("redirect", "1"))
        assert r.status_code == 200
        assert r.history[0].status_code == 302
        assert r.history[0].is_redirect

    def test_HTTP_307_ALLOW_REDIRECT_POST(self, httpbin):
        r = requests.post(
            httpbin("redirect-to"),
            data="test",
            params={"url": "post", "status_code": 307},
        )
        assert r.status_code == 200
        assert r.history[0].status_code == 307
        assert r.history[0].is_redirect
        assert r.json()["data"] == "test"

    @pytest.mark.xfail(reason="Receives 501 Not Implemented instead of 200")
    def test_HTTP_307_ALLOW_REDIRECT_POST_WITH_SEEKABLE(self, httpbin):
        byte_str = b"test"
        r = requests.post(
            httpbin("redirect-to"),
            data=io.BytesIO(byte_str),
            params={"url": "post", "status_code": 307},
        )
        assert r.status_code == 200
        assert r.history[0].status_code == 307
        assert r.history[0].is_redirect
        assert r.json()["data"] == byte_str.decode("utf-8")

    @pytest.mark.xfail(
        reason="""
        - HTTPX uses max_redirects=30 by default, while Requests uses 20.
        - TooManyRedirects.request.url refers to the original URL, not the Location
        of the previous redirect response.
        """
    )
    def test_HTTP_302_TOO_MANY_REDIRECTS(self, httpbin):
        try:
            requests.get(httpbin("relative-redirect", "50"))
        except TooManyRedirects as e:
            url = httpbin("relative-redirect", "20")
            assert e.request.url == url
            assert e.response.url == url
            assert len(e.response.history) == 30
        else:
            pytest.fail("Expected redirect to raise TooManyRedirects but it did not")

    @pytest.mark.xfail(reason="request.url is not changed by HTTPX")
    def test_HTTP_302_TOO_MANY_REDIRECTS_WITH_PARAMS(self, httpbin):
        s = requests.session()
        s.max_redirects = 5
        try:
            s.get(httpbin("relative-redirect", "50"))
        except TooManyRedirects as e:
            url = httpbin("relative-redirect", "45")
            assert e.request.url == url
            assert e.response.url == url
            assert len(e.response.history) == 5
        else:
            pytest.fail(
                "Expected custom max number of redirects to be respected but was not"
            )

    def test_http_301_changes_post_to_get(self, httpbin):
        r = requests.post(httpbin("status", "301"))
        assert r.status_code == 200
        assert r.request.method == "GET"
        assert r.history[0].status_code == 301
        assert r.history[0].is_redirect

    def test_http_301_doesnt_change_head_to_get(self, httpbin):
        r = requests.head(httpbin("status", "301"), allow_redirects=True)
        assert r.status_code == 200
        assert r.request.method == "HEAD"
        assert r.history[0].status_code == 301
        assert r.history[0].is_redirect

    def test_http_302_changes_post_to_get(self, httpbin):
        r = requests.post(httpbin("status", "302"))
        assert r.status_code == 200
        assert r.request.method == "GET"
        assert r.history[0].status_code == 302
        assert r.history[0].is_redirect

    def test_http_302_doesnt_change_head_to_get(self, httpbin):
        r = requests.head(httpbin("status", "302"), allow_redirects=True)
        assert r.status_code == 200
        assert r.request.method == "HEAD"
        assert r.history[0].status_code == 302
        assert r.history[0].is_redirect

    def test_http_303_changes_post_to_get(self, httpbin):
        r = requests.post(httpbin("status", "303"))
        assert r.status_code == 200
        assert r.request.method == "GET"
        assert r.history[0].status_code == 303
        assert r.history[0].is_redirect

    def test_http_303_doesnt_change_head_to_get(self, httpbin):
        r = requests.head(httpbin("status", "303"), allow_redirects=True)
        assert r.status_code == 200
        assert r.request.method == "HEAD"
        assert r.history[0].status_code == 303
        assert r.history[0].is_redirect

    @pytest.mark.xfail(
        reason="""
        No resolve_redirects method on httpx.Client.
        (Could be changed to use BaseResponse.next, but it is an async-only API.)
        """,
        raises=AttributeError,
    )
    def test_header_and_body_removal_on_redirect(self, httpbin):
        purged_headers = ("Content-Length", "Content-Type")
        ses = requests.Session()
        resp = ses.request("POST", httpbin("post"), data={"test": "data"})

        # Mimic a redirect response
        resp.status_code = 302
        resp.headers["location"] = "get"

        # Run request through resolve_redirects
        next_resp = next(ses.resolve_redirects(resp, resp.request))
        assert next_resp.request.body is None
        for header in purged_headers:
            assert header not in next_resp.request.headers

    @pytest.mark.xfail(
        reason="""
        No resolve_redirects method on httpx.Client.
        (Could be changed to use BaseResponse.next, but it is an async-only API.)
        """,
        raises=AttributeError,
    )
    def test_transfer_enc_removal_on_redirect(self, httpbin):
        purged_headers = ("Transfer-Encoding", "Content-Type")
        ses = requests.Session()
        req = requests.Request("POST", httpbin("post"), data=(b"x" for x in range(1)))
        assert "Transfer-Encoding" in req.headers

        # Create Response to avoid https://github.com/kevin1024/pytest-httpbin/issues/33
        resp = requests.Response(status_code=302)
        resp.raw = io.BytesIO(b"the content")
        resp.request = req
        setattr(resp.raw, "release_conn", lambda *args: args)

        # Mimic a redirect response
        resp.headers["location"] = httpbin("get")

        # Run request through resolve_redirect
        next_resp = next(ses.resolve_redirects(resp, req))
        assert next_resp.request.body is None
        for header in purged_headers:
            assert header not in next_resp.request.headers

    def test_fragment_maintained_on_redirect(self, httpbin):
        fragment = "#view=edit&token=hunter2"
        r = requests.get(httpbin("redirect-to?url=get") + fragment)

        assert len(r.history) > 0
        assert r.history[0].request.url == httpbin("redirect-to?url=get") + fragment
        assert r.url == httpbin("get") + fragment

    def test_HTTP_200_OK_GET_WITH_PARAMS(self, httpbin):
        heads = {"User-agent": "Mozilla/5.0"}

        r = requests.get(httpbin("user-agent"), headers=heads)

        assert heads["User-agent"] in r.text
        assert r.status_code == 200

    def test_HTTP_200_OK_GET_WITH_MIXED_PARAMS(self, httpbin):
        heads = {"User-agent": "Mozilla/5.0"}

        r = requests.get(
            httpbin("get") + "?test=true", params={"q": "test"}, headers=heads
        )
        assert r.status_code == 200

    def test_set_cookie_on_301(self, httpbin):
        s = requests.session()
        url = httpbin("cookies/set?foo=bar")
        s.get(url)
        assert s.cookies["foo"] == "bar"

    def test_cookie_sent_on_redirect(self, httpbin):
        s = requests.session()
        s.get(httpbin("cookies/set?foo=bar"))
        r = s.get(httpbin("redirect/1"))  # redirects to httpbin('get')
        assert "Cookie" in r.json()["headers"]

    def test_cookie_removed_on_expire(self, httpbin):
        s = requests.session()
        s.get(httpbin("cookies/set?foo=bar"))
        assert s.cookies["foo"] == "bar"
        s.get(
            httpbin("response-headers"),
            params={"Set-Cookie": "foo=deleted; expires=Thu, 01-Jan-1970 00:00:01 GMT"},
        )
        assert "foo" not in s.cookies

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="Quotes are badly escaped")
    def test_cookie_quote_wrapped(self, httpbin):
        s = requests.session()
        s.get(httpbin('cookies/set?foo="bar:baz"'))
        assert s.cookies["foo"] == '"bar:baz"'

    def test_cookie_persists_via_api(self, httpbin):
        s = requests.session()
        r = s.get(httpbin("redirect/1"), cookies={"foo": "bar"})
        assert "foo" in r.request.headers["Cookie"]
        assert "foo" in r.history[0].request.headers["Cookie"]

    def test_request_cookie_overrides_session_cookie(self, httpbin):
        s = requests.session()
        s.cookies["foo"] = "bar"
        r = s.get(httpbin("cookies"), cookies={"foo": "baz"})
        assert r.json()["cookies"]["foo"] == "baz"
        # Session cookie should not be modified
        assert s.cookies["foo"] == "bar"

    def test_request_cookies_not_persisted(self, httpbin):
        s = requests.session()
        s.get(httpbin("cookies"), cookies={"foo": "baz"})
        # Sending a request with cookies should not add cookies to the session
        assert not s.cookies

    def test_generic_cookiejar_works(self, httpbin):
        cookies = requests.Cookies(cookielib.CookieJar())
        cookies.set("foo", "bar")
        s = requests.session()
        s.cookies = cookies
        r = s.get(httpbin("cookies"))
        # Make sure the cookie was sent
        assert r.json()["cookies"]["foo"] == "bar"

    def test_param_cookiejar_works(self, httpbin):
        cookies = requests.Cookies(cookielib.CookieJar())
        cookies.set("foo", "bar")
        s = requests.session()
        r = s.get(httpbin("cookies"), cookies=cookies)
        # Make sure the cookie was sent
        assert r.json()["cookies"]["foo"] == "bar"

    @pytest.mark.skip("*Probably* not applicable to HTTPX")
    def test_cookielib_cookiejar_on_redirect(self, httpbin):
        """Tests resolve_redirect doesn't fail when merging cookies
        with non-RequestsCookieJar cookiejar.

        See GH #3579
        """
        cj = cookiejar_from_dict({"foo": "bar"}, cookielib.CookieJar())
        s = requests.Session()
        s.cookies = cookiejar_from_dict({"cookie": "tasty"})

        # Prepare request without using Session
        req = requests.Request("GET", httpbin("headers"), cookies=cj)
        prep_req = req.prepare()

        # Send request and simulate redirect
        resp = s.send(prep_req)
        resp.status_code = 302
        resp.headers["location"] = httpbin("get")
        redirects = s.resolve_redirects(resp, prep_req)
        resp = next(redirects)

        # Verify CookieJar isn't being converted to RequestsCookieJar
        assert isinstance(prep_req._cookies, cookielib.CookieJar)
        assert isinstance(resp.request._cookies, cookielib.CookieJar)
        assert not isinstance(resp.request._cookies, requests.cookies.RequestsCookieJar)

        cookies = {}
        for c in resp.request._cookies:
            cookies[c.name] = c.value
        assert cookies["foo"] == "bar"
        assert cookies["cookie"] == "tasty"

    def test_requests_in_history_are_not_overridden(self, httpbin):
        resp = requests.get(httpbin("redirect/3"))
        urls = [r.url for r in resp.history]
        req_urls = [r.request.url for r in resp.history]
        assert urls == req_urls

    def test_history_is_always_a_list(self, httpbin):
        """Show that even with redirects, Response.history is always a list."""
        resp = requests.get(httpbin("get"))
        assert isinstance(resp.history, list)
        resp = requests.get(httpbin("redirect/1"))
        assert isinstance(resp.history, list)
        assert not isinstance(resp.history, tuple)

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="'NoneType' object has no attribute 'encode'")
    def test_headers_on_session_with_None_are_not_sent(self, httpbin):
        """Do not send headers in Session.headers with None values."""
        ses = requests.Session()
        ses.headers["Accept-Encoding"] = None
        resp = ses.get(httpbin("get"))
        assert "Accept-Encoding" not in resp.request.headers

    def test_headers_preserve_order(self, httpbin):
        """Preserve order when headers provided as OrderedDict."""
        ses = requests.Session()
        ses.headers = collections.OrderedDict()
        ses.headers["Accept-Encoding"] = "identity"
        ses.headers["First"] = "1"
        ses.headers["Second"] = "2"
        headers = collections.OrderedDict([("Third", "3"), ("Fourth", "4")])
        headers["Fifth"] = "5"
        headers["Second"] = "222"
        resp = ses.get(httpbin("get"), headers=headers)
        items = list(resp.request.headers.items())

        # Remove headers automatically added by HTTPX.
        while items[0][0] != "accept-encoding":
            items.pop(0)

        assert items[0] == ("accept-encoding", "identity")
        assert items[1] == ("first", "1")
        assert items[2] == ("second", "222")
        assert items[3] == ("third", "3")
        assert items[4] == ("fourth", "4")
        assert items[5] == ("fifth", "5")

    @pytest.mark.parametrize("key", ("User-agent", "user-agent"))
    def test_user_agent_transfers(self, httpbin, key):

        heads = {key: "Mozilla/5.0 (github.com/psf/requests)"}

        r = requests.get(httpbin("user-agent"), headers=heads)
        assert heads[key] in r.text

    def test_HTTP_200_OK_HEAD(self, httpbin):
        r = requests.head(httpbin("get"))
        assert r.status_code == 200

    def test_HTTP_200_OK_PUT(self, httpbin):
        r = requests.put(httpbin("put"))
        assert r.status_code == 200

    def test_BASICAUTH_TUPLE_HTTP_200_OK_GET(self, httpbin):
        auth = ("user", "pass")
        url = httpbin("basic-auth", "user", "pass")

        r = requests.get(url, auth=auth)
        assert r.status_code == 200

        r = requests.get(url)
        assert r.status_code == 401

        s = requests.session()
        s.auth = auth
        r = s.get(url)
        assert r.status_code == 200

    @pytest.mark.parametrize(
        "username, password",
        (
            ("user", "pass"),
            ("имя".encode("utf-8"), "пароль".encode("utf-8")),
            pytest.param(
                42,
                42,
                marks=[
                    pytest.mark.httpx_bug,
                    pytest.mark.xfail(
                        reason=(
                            "HTTPX does not coerce username or password to strings. "
                            "We should probably validate them - the coercion behavior "
                            " is planned for removal in Requests 3."
                        )
                    ),
                ],
            ),
            pytest.param(
                None,
                None,
                marks=[
                    pytest.mark.httpx_bug,
                    pytest.mark.xfail(
                        reason="HTTPX does not coerce username or password to strings, "
                        "but this behavior is planned for removal in Requests 3"
                    ),
                ],
            ),
        ),
    )
    def test_set_basicauth(self, httpbin, username, password):
        auth = (username, password)
        url = httpbin("get")
        resp = requests.get(url, auth=auth)
        r = resp.request
        assert r.headers["Authorization"] == build_basic_auth_header(username, password)

    def test_basicauth_encodes_byte_strings(self, httpbin):
        """Ensure b'test' formats as the byte string "test" rather
        than the unicode string "b'test'" in Python 3.
        """
        auth = (b"\xc5\xafsername", b"test\xc6\xb6")
        resp = requests.get(httpbin("get"), auth=auth)
        r = resp.request
        assert r.headers["Authorization"] == "Basic xa9zZXJuYW1lOnRlc3TGtg=="

    @pytest.mark.parametrize(
        "url, exception",
        (
            # Connecting to an unknown domain should raise a ConnectionError
            pytest.param(
                "http://doesnotexist.google.com",
                ConnectionError,
                marks=pytest.mark.xfail(
                    reason=(
                        "Not really a bug, but we could probably wrap this "
                        "into a friendlier HTTPX-specific exception."
                    ),
                    raises=socket.gaierror,
                ),
            ),
            # Connecting to an invalid port should raise a ConnectionError
            pytest.param(
                "http://localhost:1",
                ConnectionError,
                marks=pytest.mark.xfail(
                    reason=(
                        "Not really a bug, but we could probably wrap this "
                        "into a friendlier HTTPX-specific exception."
                    ),
                    raises=OSError,
                ),
            ),
            # Inputing a URL that cannot be parsed should raise an InvalidURL error
            ("http://fe80::5054:ff:fe5a:fc0", InvalidURL),
        ),
    )
    def test_errors(self, url, exception):
        with pytest.raises(exception):
            requests.get(url, timeout=1)

    @pytest.mark.xfail(reason="Proxies are not implemented yet")
    def test_proxy_error(self):
        # any proxy related error (address resolution, no route to host, etc) should result in a ProxyError
        with pytest.raises(ProxyError):
            requests.get(
                "http://localhost:1", proxies={"http": "non-resolvable-address"}
            )

    @pytest.mark.xfail(reason="Proxies are not implemented yet")
    def test_proxy_error_on_bad_url(self, httpbin, httpbin_secure):
        with pytest.raises(InvalidProxyURL):
            requests.get(httpbin_secure(), proxies={"https": "http:/badproxyurl:3128"})

        with pytest.raises(InvalidProxyURL):
            requests.get(httpbin(), proxies={"http": "http://:8080"})

        with pytest.raises(InvalidProxyURL):
            requests.get(httpbin_secure(), proxies={"https": "https://"})

        with pytest.raises(InvalidProxyURL):
            requests.get(httpbin(), proxies={"http": "http:///example.com:8080"})

    def test_basicauth_with_netrc(self, httpbin):
        wrong_auth = ("wronguser", "", "wrongpass")
        url = httpbin("basic-auth", "user", "pass")

        # Generate a .netrc file.
        netrc_path = "tests/compat/.netrc"
        with open(netrc_path, "w", encoding="utf-8") as netrc:
            machine = httpbin.url.replace("http://", "")
            netrc.write(f"machine {machine}\n")
            netrc.write("login user\n")
            netrc.write("password pass\n")

        os.environ["NETRC"] = netrc_path

        try:
            # Should use netrc and work.
            r = requests.get(url, trust_env=True)
            assert r.status_code == 200

            # Given auth should override and fail.
            r = requests.get(url, auth=wrong_auth, trust_env=True)
            assert r.status_code == 401

            s = requests.session(trust_env=True)

            # Should use netrc and work.
            r = s.get(url, trust_env=True)
            assert r.status_code == 200

            # Given auth should override and fail.
            s.auth = wrong_auth
            r = s.get(url, trust_env=True)
            assert r.status_code == 401
        finally:
            os.environ.pop("NETRC")

    @pytest.mark.xfail(reason="Digest not implemented yet")
    def test_DIGEST_HTTP_200_OK_GET(self, httpbin):

        for authtype in self.digest_auth_algo:
            auth = HTTPDigestAuth("user", "pass")
            url = httpbin("digest-auth", "auth", "user", "pass", authtype, "never")

            r = requests.get(url, auth=auth)
            assert r.status_code == 200

            r = requests.get(url)
            assert r.status_code == 401
            print(r.headers["WWW-Authenticate"])

            s = requests.session()
            s.auth = HTTPDigestAuth("user", "pass")
            r = s.get(url)
            assert r.status_code == 200

    @pytest.mark.xfail(reason="Digest not implemented yet")
    def test_DIGEST_AUTH_RETURNS_COOKIE(self, httpbin):

        for authtype in self.digest_auth_algo:
            url = httpbin("digest-auth", "auth", "user", "pass", authtype)
            auth = HTTPDigestAuth("user", "pass")
            r = requests.get(url)
            assert r.cookies["fake"] == "fake_value"

            r = requests.get(url, auth=auth)
            assert r.status_code == 200

    @pytest.mark.xfail(reason="Digest not implemented yet")
    def test_DIGEST_AUTH_SETS_SESSION_COOKIES(self, httpbin):

        for authtype in self.digest_auth_algo:
            url = httpbin("digest-auth", "auth", "user", "pass", authtype)
            auth = HTTPDigestAuth("user", "pass")
            s = requests.Session()
            s.get(url, auth=auth)
            assert s.cookies["fake"] == "fake_value"

    @pytest.mark.xfail(reason="Digest not implemented yet")
    def test_DIGEST_STREAM(self, httpbin):

        for authtype in self.digest_auth_algo:
            auth = HTTPDigestAuth("user", "pass")
            url = httpbin("digest-auth", "auth", "user", "pass", authtype)

            r = requests.get(url, auth=auth, stream=True)
            assert r.raw.read() != b""

            r = requests.get(url, auth=auth, stream=False)
            assert r.raw.read() == b""

    @pytest.mark.xfail(reason="Digest not implemented yet")
    def test_DIGESTAUTH_WRONG_HTTP_401_GET(self, httpbin):

        for authtype in self.digest_auth_algo:
            auth = HTTPDigestAuth("user", "wrongpass")
            url = httpbin("digest-auth", "auth", "user", "pass", authtype)

            r = requests.get(url, auth=auth)
            assert r.status_code == 401

            r = requests.get(url)
            assert r.status_code == 401

            s = requests.session()
            s.auth = auth
            r = s.get(url)
            assert r.status_code == 401

    @pytest.mark.xfail(reason="Digest not implemented yet")
    def test_DIGESTAUTH_QUOTES_QOP_VALUE(self, httpbin):

        for authtype in self.digest_auth_algo:
            auth = HTTPDigestAuth("user", "pass")
            url = httpbin("digest-auth", "auth", "user", "pass", authtype)

            r = requests.get(url, auth=auth)
            assert '"auth"' in r.request.headers["Authorization"]

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="'files' is not validated", raises=AttributeError)
    def test_POSTBIN_GET_POST_FILES(self, httpbin):

        url = httpbin("post")
        requests.post(url).raise_for_status()

        post1 = requests.post(url, data={"some": "data"})
        assert post1.status_code == 200

        with open("setup.py") as f:
            post2 = requests.post(url, files={"some": f})
        assert post2.status_code == 200

        post4 = requests.post(url, data='[{"some": "json"}]')
        assert post4.status_code == 200

        with pytest.raises(ValueError):
            requests.post(url, files=["bad file data"])

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="'files' is not validated", raises=AttributeError)
    def test_invalid_files_input(self, httpbin):

        url = httpbin("post")
        post = requests.post(url, files={"random-file-1": None, "random-file-2": 1})
        assert b'name="random-file-1"' not in post.request.body
        assert b'name="random-file-2"' in post.request.body

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            "HTTPX expects data objects to have '__iter__', "
            "and does not fall back to the stream API."
        ),
        raises=AssertionError,
    )
    def test_POSTBIN_SEEKED_OBJECT_WITH_NO_ITER(self, httpbin):
        class TestStream(object):
            def __init__(self, data):
                self.data = data.encode()
                self.length = len(self.data)
                self.index = 0

            def __len__(self):
                return self.length

            def read(self, size=None):
                if size:
                    ret = self.data[self.index : self.index + size]
                    self.index += size
                else:
                    ret = self.data[self.index :]
                    self.index = self.length
                return ret

            def tell(self):
                return self.index

            def seek(self, offset, where=0):
                if where == 0:
                    self.index = offset
                elif where == 1:
                    self.index += offset
                elif where == 2:
                    self.index = self.length + offset

        test = TestStream("test")
        post1 = requests.post(httpbin("post"), data=test)
        assert post1.status_code == 200
        assert post1.json()["data"] == "test"

        test = TestStream("test")
        test.seek(2)
        post2 = requests.post(httpbin("post"), data=test)
        assert post2.status_code == 200
        assert post2.json()["data"] == "st"

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="'files' is not validated", raises=AttributeError)
    def test_POSTBIN_GET_POST_FILES_WITH_DATA(self, httpbin):

        url = httpbin("post")
        requests.post(url).raise_for_status()

        post1 = requests.post(url, data={"some": "data"})
        assert post1.status_code == 200

        with open("setup.py") as f:
            post2 = requests.post(url, data={"some": "data"}, files={"some": f})
        assert post2.status_code == 200

        post4 = requests.post(url, data='[{"some": "json"}]')
        assert post4.status_code == 200

        with pytest.raises(ValueError):
            requests.post(url, files=["bad file data"])

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            """
            - HTTPX calls next() on the body iterator without calling iter() first,
            but this example iterable doesn't define __next__().
            - Even if that was fixed, HTTPX makes an instance check against dict, so our
            custom mapping isn't processed correctly, making the test fail.
            """
        ),
        raises=TypeError,
    )
    def test_post_with_custom_mapping(self, httpbin):
        class CustomMapping(collections.abc.MutableMapping):
            def __init__(self, *args, **kwargs):
                self.data = dict(*args, **kwargs)

            def __delitem__(self, key):
                del self.data[key]

            def __getitem__(self, key):
                return self.data[key]

            def __setitem__(self, key, value):
                self.data[key] = value

            def __iter__(self):
                return iter(self.data)

            def __len__(self):
                return len(self.data)

        data = CustomMapping({"some": "data"})
        url = httpbin("post")
        found_json = requests.post(url, data=data).json().get("form")
        assert found_json == {"some": "data"}

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="HTTPX does not check this case")
    def test_conflicting_post_params(self, httpbin):
        url = httpbin("post")
        with open("setup.py") as f:
            with pytest.raises(ValueError):
                requests.post(url, data='[{"some": "data"}]', files={"some": f})

    @pytest.mark.xfail(reason="HTTPX does not provide Response.ok")
    def test_request_ok_set(self, httpbin):
        r = requests.get(httpbin("status", "404"))
        assert not r.ok

    @pytest.mark.xfail(reason="HTTPX does not provide Response.ok")
    def test_status_raising(self, httpbin):
        r = requests.get(httpbin("status", "404"))
        with pytest.raises(requests.exceptions.HTTPError):
            r.raise_for_status()

        r = requests.get(httpbin("status", "500"))
        assert not r.ok

    def test_decompress_gzip(self, httpbin):
        r = requests.get(httpbin("gzip"))
        r.content.decode("ascii")

    @pytest.mark.parametrize(
        "url, params",
        (
            ("/get", {"foo": "føø"}),
            ("/get", {"føø": "føø"}),
            ("/get", {"føø": "føø"}),
            ("/get", {"foo": "foo"}),
            ("ø", {"foo": "foo"}),
        ),
    )
    def test_unicode_get(self, httpbin, url, params):
        requests.get(httpbin(url), params=params)

    def test_unicode_header_name(self, httpbin):
        requests.put(
            httpbin("put"),
            headers={str("Content-Type"): "application/octet-stream"},
            data="\xff",
        )  # compat.str is unicode.

    def test_pyopenssl_redirect(self, httpbin_secure, httpbin_ca_bundle):
        requests.get(httpbin_secure("status", "301"), verify=httpbin_ca_bundle)

    def test_invalid_ca_certificate_path(self, httpbin_secure):
        INVALID_PATH = "/garbage"
        with pytest.raises(IOError) as e:
            requests.get(httpbin_secure(), verify=INVALID_PATH)
        assert str(e.value) == (
            "Could not find a suitable TLS CA certificate bundle, "
            "invalid path: {}".format(INVALID_PATH)
        )

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="Fails with 'No such file or directory' instead")
    def test_invalid_ssl_certificate_files(self, httpbin_secure):
        INVALID_PATH = "/garbage"
        with pytest.raises(IOError) as e:
            requests.get(httpbin_secure(), cert=INVALID_PATH)
        assert str(
            e.value
        ) == "Could not find the TLS certificate file, invalid path: {}".format(
            INVALID_PATH
        )

        with pytest.raises(IOError) as e:
            requests.get(httpbin_secure(), cert=(".", INVALID_PATH))
        assert str(
            e.value
        ) == "Could not find the TLS key file, invalid path: {}".format(INVALID_PATH)

    def test_http_with_certificate(self, httpbin):
        r = requests.get(httpbin(), cert=".")
        assert r.status_code == 200

    @pytest.mark.xfail(reason="HTTPX does not emit such warnings - probably should?")
    def test_https_warnings(self, httpbin_secure, httpbin_ca_bundle):
        """warnings are emitted with requests.get"""
        if HAS_MODERN_SSL or HAS_PYOPENSSL:
            warnings_expected = ("SubjectAltNameWarning",)
        else:
            warnings_expected = (
                "SNIMissingWarning",
                "InsecurePlatformWarning",
                "SubjectAltNameWarning",
            )

        with pytest.warns(None) as warning_records:
            warnings.simplefilter("always")
            requests.get(httpbin_secure("status", "200"), verify=httpbin_ca_bundle)

        warning_records = [
            item
            for item in warning_records
            if item.category.__name__ != "ResourceWarning"
        ]

        warnings_category = tuple(item.category.__name__ for item in warning_records)
        assert warnings_category == warnings_expected

    def test_certificate_failure(self, httpbin_secure):
        """
        When underlying SSL problems occur, an SSLError is raised.
        """
        with pytest.raises(ssl.SSLError):
            # Our local httpbin does not have a trusted CA, so this call will
            # fail if we use our default trust bundle.
            requests.get(httpbin_secure("status", "200"))

    # vvv TODO vvv

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason="list repr gets URL-encoded: '/get?test=%5B%27foo%27%2C+%27baz%27%5D'"
    )
    def test_urlencoded_get_query_multivalued_param(self, httpbin):
        r = requests.get(httpbin("get"), params={"test": ["foo", "baz"]})
        assert r.status_code == 200
        assert r.url == httpbin("get?test=foo&test=baz")

    def test_form_encoded_post_query_multivalued_element(self, httpbin):
        r = requests.Request(
            method="POST", url=httpbin("post"), data=dict(test=["foo", "baz"])
        )
        assert r.content == b"test=foo&test=baz"

    def test_different_encodings_dont_break_post(self, httpbin):
        r = requests.post(
            httpbin("post"),
            data={"stuff": json.dumps({"a": 123})},
            params={"blah": "asdf1234"},
            files={"file": ("test_requests.py", open(__file__, "rb"))},
        )
        assert r.status_code == 200

    @pytest.mark.parametrize(
        "data",
        (
            {"stuff": "ëlïxr"},
            {"stuff": "ëlïxr".encode("utf-8")},
            {"stuff": "elixr"},
            {"stuff": "elixr".encode("utf-8")},
        ),
    )
    def test_unicode_multipart_post(self, httpbin, data):
        r = requests.post(
            httpbin("post"),
            data=data,
            files={"file": ("test_requests.py", open(__file__, "rb"))},
        )
        assert r.status_code == 200

    @pytest.mark.xfail(reason="HTTPX disallows bytes form keys - probably OK.")
    def test_unicode_multipart_post_fieldnames(self, httpbin):
        filename = os.path.splitext(__file__)[0] + ".py"
        r = requests.Request(
            method="POST",
            url=httpbin("post"),
            data={"stuff".encode("utf-8"): "elixr"},
            files={"file": ("test_requests.py", open(filename, "rb"))},
        )
        prep = r.prepare()
        assert b'name="stuff"' in prep.body
        assert b"name=\"b'stuff'\"" not in prep.body

    def test_unicode_method_name(self, httpbin):
        files = {"file": open(__file__, "rb")}
        r = requests.request(method="POST", url=httpbin("post"), files=files)
        assert r.status_code == 200

    def test_unicode_method_name_with_request_object(self, httpbin):
        files = {"file": open(__file__, "rb")}
        resp = requests.request("POST", httpbin("post"), files=files)
        req = resp.request
        assert isinstance(req.method, str)
        assert req.method == "POST"
        assert resp.status_code == 200

    @pytest.mark.skip("HTTPX automatically prepares requests")
    def test_non_prepared_request_error(self):
        s = requests.Session()
        req = requests.Request(u("POST"), "/")

        with pytest.raises(ValueError) as e:
            s.send(req)
        assert str(e.value) == "You can only send PreparedRequests."

    def test_custom_content_type(self, httpbin):
        r = requests.post(
            httpbin("post"),
            data={"stuff": json.dumps({"a": 123})},
            files={
                "file1": ("test_requests.py", open(__file__, "rb")),
                "file2": (
                    "test_requests",
                    open(__file__, "rb"),
                    "text/py-content-type",
                ),
            },
        )
        assert r.status_code == 200
        assert b"text/py-content-type" in r.request.content

    @pytest.mark.skip(reason="HTTPX doesn't have a concept of hooks")
    def test_hook_receives_request_arguments(self, httpbin):
        def hook(resp, **kwargs):
            assert resp is not None
            assert kwargs != {}

        s = requests.Session()
        r = requests.Request("GET", httpbin(), hooks={"response": hook})
        prep = s.prepare_request(r)
        s.send(prep)

    @pytest.mark.skip(reason="HTTPX doesn't have a concept of hooks")
    def test_session_hooks_are_used_with_no_request_hooks(self, httpbin):
        hook = lambda x, *args, **kwargs: x
        s = requests.Session()
        s.hooks["response"].append(hook)
        r = requests.Request("GET", httpbin())
        prep = s.prepare_request(r)
        assert prep.hooks["response"] != []
        assert prep.hooks["response"] == [hook]

    @pytest.mark.skip(reason="HTTPX doesn't have a concept of hooks")
    def test_session_hooks_are_overridden_by_request_hooks(self, httpbin):
        hook1 = lambda x, *args, **kwargs: x
        hook2 = lambda x, *args, **kwargs: x
        assert hook1 is not hook2
        s = requests.Session()
        s.hooks["response"].append(hook2)
        r = requests.Request("GET", httpbin(), hooks={"response": [hook1]})
        prep = s.prepare_request(r)
        assert prep.hooks["response"] == [hook1]

    @pytest.mark.skip(reason="HTTPX doesn't have a concept of hooks")
    def test_prepared_request_hook(self, httpbin):
        def hook(resp, **kwargs):
            resp.hook_working = True
            return resp

        req = requests.Request("GET", httpbin(), hooks={"response": hook})
        prep = req.prepare()

        s = requests.Session()
        s.proxies = getproxies()
        resp = s.send(prep)

        assert hasattr(resp, "hook_working")

    def test_prepared_from_session(self, httpbin):
        def dummy_auth(request):
            request.headers["Dummy-Auth-Test"] = "dummy-auth-test-ok"
            return request

        s = requests.Session()
        s.auth = dummy_auth

        resp = s.request("GET", httpbin("headers"))

        assert resp.json()["headers"]["Dummy-Auth-Test"] == "dummy-auth-test-ok"

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            "HTTPX doesn't handle URLs passed as bytes: "
            "'bytes' object has no attribute '_uri_reference'"
        )
    )
    def test_prepare_request_with_bytestring_url(self):
        resp = requests.request("GET", b"https://httpbin.org/")
        assert resp.request.url == "https://httpbin.org/"

    def test_request_with_bytestring_host(self, httpbin):
        s = requests.Session()
        resp = s.request(
            "GET",
            httpbin("cookies/set?cookie=value"),
            allow_redirects=False,
            headers={"Host": b"httpbin.org"},
        )
        assert resp.cookies.get("cookie") == "value"

    def test_links(self):
        r = requests.Response(status_code=200)
        r.headers = {
            "cache-control": "public, max-age=60, s-maxage=60",
            "connection": "keep-alive",
            "content-encoding": "gzip",
            "content-type": "application/json; charset=utf-8",
            "date": "Sat, 26 Jan 2013 16:47:56 GMT",
            "etag": '"6ff6a73c0e446c1f61614769e3ceb778"',
            "last-modified": "Sat, 26 Jan 2013 16:22:39 GMT",
            "link": (
                "<https://api.github.com/users/kennethreitz/repos?"
                'page=2&per_page=10>; rel="next", <https://api.github.'
                "com/users/kennethreitz/repos?page=7&per_page=10>; "
                ' rel="last"'
            ),
            "server": "GitHub.com",
            "status": "200 OK",
            "vary": "Accept",
            "x-content-type-options": "nosniff",
            "x-github-media-type": "github.beta",
            "x-ratelimit-limit": "60",
            "x-ratelimit-remaining": "57",
        }
        assert r.links["next"]["rel"] == "next"

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(reason="Cookies.set() doesn't have 'secure' and 'rest' options")
    def test_cookie_parameters(self):
        key = "some_cookie"
        value = "some_value"
        secure = True
        domain = "test.com"
        rest = {"HttpOnly": True}

        jar = requests.Cookies()
        jar.set(key, value, secure=secure, domain=domain, rest=rest)

        assert len(jar) == 1
        assert "some_cookie" in jar

        cookie = list(jar)[0]
        assert cookie.secure == secure
        assert cookie.domain == domain
        assert cookie._rest["HttpOnly"] == rest["HttpOnly"]

    def test_cookie_as_dict_keeps_len(self):
        key = "some_cookie"
        value = "some_value"

        key1 = "some_cookie1"
        value1 = "some_value1"

        jar = requests.Cookies()
        jar.set(key, value)
        jar.set(key1, value1)

        d1 = dict(jar)
        d2 = dict(jar.items())

        assert len(jar) == 2
        assert len(d1) == 2
        assert len(d2) == 2

    def test_cookie_as_dict_keeps_items(self):
        key = "some_cookie"
        value = "some_value"

        key1 = "some_cookie1"
        value1 = "some_value1"

        jar = requests.Cookies()
        jar.set(key, value)
        jar.set(key1, value1)

        d1 = dict(jar)
        d2 = dict(jar.items())

        assert d1["some_cookie"] == "some_value"
        assert d2["some_cookie1"] == "some_value1"

    def test_cookie_as_dict_keys(self):
        key = "some_cookie"
        value = "some_value"

        key1 = "some_cookie1"
        value1 = "some_value1"

        jar = requests.Cookies()
        jar.set(key, value)
        jar.set(key1, value1)

        keys = jar.keys()
        assert list(keys) == [key, key1]
        # make sure one can use keys multiple times
        assert list(keys) == list(keys)

    def test_cookie_as_dict_values(self):
        key = "some_cookie"
        value = "some_value"

        key1 = "some_cookie1"
        value1 = "some_value1"

        jar = requests.Cookies()
        jar.set(key, value)
        jar.set(key1, value1)

        values = jar.values()
        assert list(values) == [value, value1]
        # make sure one can use values multiple times
        assert list(values) == list(values)

    def test_cookie_as_dict_items(self):
        key = "some_cookie"
        value = "some_value"

        key1 = "some_cookie1"
        value1 = "some_value1"

        jar = requests.Cookies()
        jar.set(key, value)
        jar.set(key1, value1)

        items = jar.items()
        assert list(items) == [(key, value), (key1, value1)]
        # make sure one can use items multiple times
        assert list(items) == list(items)

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason="'key in jar' fails with CookieConflict",
        raises=requests.exceptions.CookieConflict,
    )
    def test_cookie_duplicate_names_different_domains(self):
        key = "some_cookie"
        value = "some_value"
        domain1 = "test1.com"
        domain2 = "test2.com"

        jar = requests.Cookies()
        jar.set(key, value, domain=domain1)
        jar.set(key, value, domain=domain2)
        assert key in jar
        items = jar.items()
        assert len(items) == 2

        # Verify that CookieConflictError is raised if domain is not specified
        with pytest.raises(requests.exceptions.CookieConflict):
            jar.get(key)

        # Verify that CookieConflictError is not raised if domain is specified
        cookie = jar.get(key, domain=domain1)
        assert cookie == value

    def test_cookie_duplicate_names_raises_cookie_conflict_error(self):
        key = "some_cookie"
        value = "some_value"
        path = "some_path"

        jar = requests.Cookies()
        jar.set(key, value, path=path)
        jar.set(key, value)
        with pytest.raises(requests.exceptions.CookieConflict):
            jar.get(key)

    @pytest.mark.skip("HTTPX uses a standard CookieJar, which doesn't provide .copy()")
    def test_cookie_policy_copy(self):
        class MyCookiePolicy(cookielib.DefaultCookiePolicy):
            pass

        cookies = requests.Cookies()
        cookies.jar.set_policy(MyCookiePolicy())
        assert isinstance(cookies.jar.copy().get_policy(), MyCookiePolicy)

    @pytest.mark.skip(reason="HTTPX does not provide response.elapsed")
    def test_time_elapsed_blank(self, httpbin):
        r = requests.get(httpbin("get"))
        td = r.elapsed
        total_seconds = (
            td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6
        ) / 10 ** 6
        assert total_seconds > 0.0

    @pytest.mark.xfail(reason="HTTPX uses b'' instead - which is probably better.")
    def test_empty_response_has_content_none(self):
        r = requests.Response(status_code=204)
        assert r.content is None

    def test_response_is_iterable(self):
        # NOTE: Refactored to pass `content=sio` instead of setting `r.raw`.
        sio = io.StringIO("abc")
        read_ = sio.read

        def read_mock(amt, decode_content=None):
            return read_(amt)

        setattr(sio, "read", read_mock)

        r = requests.Response(content=sio, status_code=200)
        assert next(iter(r.stream()))  # NOTE: `r.stream()` instead of `r`.
        sio.close()

    @pytest.mark.xfail(
        reason="Responses aren't iterable. Plus, this is testing private APIs."
    )
    def test_response_decode_unicode(self):
        """When called with decode_unicode, Response.iter_content should always
        return unicode.
        """
        r = requests.Response(status_code=200)
        r._content_consumed = True
        r._content = b"the content"
        r.encoding = "ascii"

        chunks = r.iter_content(decode_unicode=True)
        assert all(isinstance(chunk, str) for chunk in chunks)

        # also for streaming
        r = requests.Response()
        r.raw = io.BytesIO(b"the content")
        r.encoding = "ascii"
        chunks = r.iter_content(decode_unicode=True)
        assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.skip(reason="A regresision test that's irrelevant to us.")
    def test_response_reason_unicode(self):
        # check for unicode HTTP status
        r = requests.Response()
        r.url = "unicode URL"
        r.reason = "Komponenttia ei löydy".encode("utf-8")
        r.status_code = 404
        r.encoding = None
        assert not r.ok  # old behaviour - crashes here

    @pytest.mark.xfail(reason="HTTPX responses don't have a 'reason'.")
    def test_response_reason_unicode_fallback(self):
        # check raise_status falls back to ISO-8859-1
        r = requests.Response(500)
        reason = "Komponenttia ei löydy"
        r.reason = reason.encode("latin-1")
        r.encoding = None
        with pytest.raises(requests.exceptions.HTTPError) as e:
            r.raise_for_status()
        assert reason in e.value.args[0]

    # TODO: refactor with Response.stream()
    @pytest.mark.xfail()
    def test_response_chunk_size_type(self):
        """Ensure that chunk_size is passed as None or an integer, otherwise
        raise a TypeError.
        """
        r = requests.Response(200)
        r.raw = io.BytesIO(b"the content")
        chunks = r.iter_content(1)
        assert all(len(chunk) == 1 for chunk in chunks)

        r = requests.Response()
        r.raw = io.BytesIO(b"the content")
        chunks = r.iter_content(None)
        assert list(chunks) == [b"the content"]

        r = requests.Response()
        r.raw = io.BytesIO(b"the content")
        with pytest.raises(TypeError):
            chunks = r.iter_content("1024")

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            "Fails with: "
            "'Can't pickle local objectClient.request.<locals>.sync_on_close'"
        )
    )
    def test_request_and_response_are_pickleable(self, httpbin):
        r = requests.get(httpbin("get"))

        # verify we can pickle the original request
        assert pickle.loads(pickle.dumps(r.request))

        # verify we can pickle the response and that we have access to
        # the original request.
        pr = pickle.loads(pickle.dumps(r))
        assert r.request.url == pr.request.url
        assert r.request.headers == pr.request.headers

    @pytest.mark.xfail(
        reason=(
            "HTTPX doesn't provide a sync '.send(request)' API, "
            "which means the final 'resp' object is a coroutine"
        ),
        raises=AttributeError,
    )
    def test_prepared_request_is_pickleable(self, httpbin):
        p = requests.Request("GET", httpbin("get"))

        # Verify PreparedRequest can be pickled and unpickled
        r = pickle.loads(pickle.dumps(p))
        assert r.url == p.url
        assert r.headers == p.headers
        assert r.content == p.content

        # Verify unpickled PreparedRequest sends properly
        s = requests.Session()
        resp = s.send(r)
        assert resp.status_code == 200

    @pytest.mark.xfail(
        reason=(
            "HTTPX doesn't provide a sync '.send(request)' API, "
            "which means the final 'resp' object is a coroutine"
        ),
        raises=AttributeError,
    )
    def test_prepared_request_with_file_is_pickleable(self, httpbin):
        files = {"file": open(__file__, "rb")}
        p = requests.Request("POST", httpbin("post"), files=files)

        # Verify PreparedRequest can be pickled and unpickled
        r = pickle.loads(pickle.dumps(p))
        assert r.url == p.url
        assert r.headers == p.headers
        assert r.content == p.content

        # Verify unpickled PreparedRequest sends properly
        s = requests.Session()
        resp = s.send(r)
        assert resp.status_code == 200

    @pytest.mark.xfail(reason="HTTPX doesn't have a concept of hooks")
    def test_prepared_request_with_hook_is_pickleable(self, httpbin):
        r = requests.Request("GET", httpbin("get"), hooks=default_hooks())
        p = r.prepare()

        # Verify PreparedRequest can be pickled
        r = pickle.loads(pickle.dumps(p))
        assert r.url == p.url
        assert r.headers == p.headers
        assert r.body == p.body
        assert r.hooks == p.hooks

        # Verify unpickled PreparedRequest sends properly
        s = requests.Session()
        resp = s.send(r)
        assert resp.status_code == 200

    @pytest.mark.skip("HTTPX prepares requests by default")
    def test_cannot_send_unprepared_requests(self, httpbin):
        r = requests.Request(url=httpbin())
        with pytest.raises(ValueError):
            requests.Session().send(r)

    def test_http_error(self):
        error = requests.exceptions.HTTPError()
        assert not error.response
        response = requests.Response(200)
        error = requests.exceptions.HTTPError(response=response)
        assert error.response == response
        error = requests.exceptions.HTTPError("message", response=response)
        assert str(error) == "message"
        assert error.response == response

    @pytest.mark.xfail(reason="HTTPX.Client uses an RLock, which isn't picklable")
    def test_session_pickling(self, httpbin):
        s = requests.Session()
        s = pickle.loads(pickle.dumps(s))
        r = s.request("GET", httpbin("get"))
        assert r.status_code == 200

    def test_fixes_1329(self, httpbin):
        """Ensure that header updates are done case-insensitively."""
        s = requests.Session()
        s.headers.update({"ACCEPT": "BOGUS"})
        s.headers.update({"accept": "application/json"})
        r = s.get(httpbin("get"))
        headers = r.request.headers
        assert headers["accept"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["ACCEPT"] == "application/json"

    def test_uppercase_scheme_redirect(self, httpbin):
        parts = urlparse(httpbin("html"))
        url = "HTTP://" + parts.netloc + parts.path
        r = requests.get(httpbin("redirect-to"), params={"url": url})
        assert r.status_code == 200
        assert str(r.url).lower() == url.lower()

    @pytest.mark.xfail(reason="HTTPX doesn't have a concept of mountable adapters")
    def test_transport_adapter_ordering(self):
        s = requests.Session()
        order = ["https://", "http://"]
        assert order == list(s.adapters)
        s.mount("http://git", HTTPAdapter())
        s.mount("http://github", HTTPAdapter())
        s.mount("http://github.com", HTTPAdapter())
        s.mount("http://github.com/about/", HTTPAdapter())
        order = [
            "http://github.com/about/",
            "http://github.com",
            "http://github",
            "http://git",
            "https://",
            "http://",
        ]
        assert order == list(s.adapters)
        s.mount("http://gittip", HTTPAdapter())
        s.mount("http://gittip.com", HTTPAdapter())
        s.mount("http://gittip.com/about/", HTTPAdapter())
        order = [
            "http://github.com/about/",
            "http://gittip.com/about/",
            "http://github.com",
            "http://gittip.com",
            "http://github",
            "http://gittip",
            "http://git",
            "https://",
            "http://",
        ]
        assert order == list(s.adapters)
        s2 = requests.Session()
        s2.adapters = {"http://": HTTPAdapter()}
        s2.mount("https://", HTTPAdapter())
        assert "http://" in s2.adapters
        assert "https://" in s2.adapters

    @pytest.mark.xfail(reason="HTTPX doesn't have a concept of mountable adapters")
    def test_session_get_adapter_prefix_matching(self):
        prefix = "https://example.com"
        more_specific_prefix = prefix + "/some/path"

        url_matching_only_prefix = prefix + "/another/path"
        url_matching_more_specific_prefix = more_specific_prefix + "/longer/path"
        url_not_matching_prefix = "https://another.example.com/"

        s = requests.Session()
        prefix_adapter = HTTPAdapter()
        more_specific_prefix_adapter = HTTPAdapter()
        s.mount(prefix, prefix_adapter)
        s.mount(more_specific_prefix, more_specific_prefix_adapter)

        assert s.get_adapter(url_matching_only_prefix) is prefix_adapter
        assert (
            s.get_adapter(url_matching_more_specific_prefix)
            is more_specific_prefix_adapter
        )
        assert s.get_adapter(url_not_matching_prefix) not in (
            prefix_adapter,
            more_specific_prefix_adapter,
        )

    @pytest.mark.xfail(reason="HTTPX doesn't have a concept of mountable adapters")
    def test_session_get_adapter_prefix_matching_mixed_case(self):
        mixed_case_prefix = "hTtPs://eXamPle.CoM/MixEd_CAse_PREfix"
        url_matching_prefix = mixed_case_prefix + "/full_url"

        s = requests.Session()
        my_adapter = HTTPAdapter()
        s.mount(mixed_case_prefix, my_adapter)

        assert s.get_adapter(url_matching_prefix) is my_adapter

    @pytest.mark.xfail(reason="HTTPX doesn't have a concept of mountable adapters")
    def test_session_get_adapter_prefix_matching_is_case_insensitive(self):
        mixed_case_prefix = "hTtPs://eXamPle.CoM/MixEd_CAse_PREfix"
        url_matching_prefix_with_different_case = (
            "HtTpS://exaMPLe.cOm/MiXeD_caSE_preFIX/another_url"
        )

        s = requests.Session()
        my_adapter = HTTPAdapter()
        s.mount(mixed_case_prefix, my_adapter)

        assert s.get_adapter(url_matching_prefix_with_different_case) is my_adapter

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason="HTTPX doesn't handle None header values (tries to .encode() them)"
    )
    def test_header_remove_is_case_insensitive(self, httpbin):
        # From issue #1321
        s = requests.Session()
        s.headers["foo"] = "bar"
        r = s.get(httpbin("get"), headers={"FOO": None})
        assert "foo" not in r.request.headers

    @pytest.mark.xfail(
        reason="HTTPX client doesn't hold query parameters anywhere",
        raises=AttributeError,
    )
    def test_params_are_merged_case_sensitive(self, httpbin):
        s = requests.Session()
        s.params["foo"] = "bar"
        r = s.get(httpbin("get"), params={"FOO": "bar"})
        assert r.json()["args"] == {"foo": "bar", "FOO": "bar"}

    def test_long_authinfo_in_url(self):
        url = "http://{}:{}@{}:9000/path?query#frag".format(
            "E8A3BE87-9E3F-4620-8858-95478E385B5B",
            "EA770032-DA4D-4D84-8CE9-29C6D910BF1E",
            "exactly-------------sixty-----------three------------characters",
        )
        r = requests.Request("GET", url)
        assert str(r.url) == url

    def test_header_keys_are_native(self, httpbin):
        headers = {"unicode": "blah", "byte".encode("ascii"): "blah"}
        r = requests.Request("GET", httpbin("get"), headers=headers)

        # This is testing that they are builtin strings. A bit weird, but there
        # we go.
        assert "unicode" in r.headers.keys()
        assert "byte" in r.headers.keys()

    def test_header_validation(self, httpbin):
        """Ensure prepare_headers regex isn't flagging valid header contents."""
        headers_ok = {
            "foo": "bar baz qux",
            "bar": "fbbq".encode("utf8"),
            "baz": "",
            "qux": "1",
        }
        r = requests.get(httpbin("get"), headers=headers_ok)
        assert r.request.headers["foo"] == headers_ok["foo"]

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            "HTTPX doesn't validate header values "
            "(and does not have an equivalent for Requests' InvalidHeader exception)"
        )
    )
    def test_header_value_not_str(self, httpbin):
        """Ensure the header value is of type string or bytes as
        per discussion in GH issue #3386
        """
        headers_int = {"foo": 3}
        headers_dict = {"bar": {"foo": "bar"}}
        headers_list = {"baz": ["foo", "bar"]}

        # Test for int
        with pytest.raises(InvalidHeader) as excinfo:
            r = requests.get(httpbin("get"), headers=headers_int)
        assert "foo" in str(excinfo.value)
        # Test for dict
        with pytest.raises(InvalidHeader) as excinfo:
            r = requests.get(httpbin("get"), headers=headers_dict)
        assert "bar" in str(excinfo.value)
        # Test for list
        with pytest.raises(InvalidHeader) as excinfo:
            r = requests.get(httpbin("get"), headers=headers_list)
        assert "baz" in str(excinfo.value)

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            "HTTPX doesn't validate header values "
            "(and does not have an equivalent for Requests' InvalidHeader exception)"
        )
    )
    def test_header_no_return_chars(self, httpbin):
        """Ensure that a header containing return character sequences raise an
        exception. Otherwise, multiple headers are created from single string.
        """
        headers_ret = {"foo": "bar\r\nbaz: qux"}
        headers_lf = {"foo": "bar\nbaz: qux"}
        headers_cr = {"foo": "bar\rbaz: qux"}

        # Test for newline
        with pytest.raises(InvalidHeader):
            r = requests.get(httpbin("get"), headers=headers_ret)
        # Test for line feed
        with pytest.raises(InvalidHeader):
            r = requests.get(httpbin("get"), headers=headers_lf)
        # Test for carriage return
        with pytest.raises(InvalidHeader):
            r = requests.get(httpbin("get"), headers=headers_cr)

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason=(
            "HTTPX doesn't validate header values "
            "(and does not have an equivalent for Requests' InvalidHeader exception)"
        )
    )
    def test_header_no_leading_space(self, httpbin):
        """Ensure headers containing leading whitespace raise
        InvalidHeader Error before sending.
        """
        headers_space = {"foo": " bar"}
        headers_tab = {"foo": "   bar"}

        # Test for whitespace
        with pytest.raises(InvalidHeader):
            r = requests.get(httpbin("get"), headers=headers_space)
        # Test for tab
        with pytest.raises(InvalidHeader):
            r = requests.get(httpbin("get"), headers=headers_tab)

    @pytest.mark.xfail(
        reason=(
            "HTTPX expects file-like objects only, e.g. ones with '.read()'. "
            "Not sure if this is a bug."
        )
    )
    @pytest.mark.parametrize("files", ("foo", b"foo", bytearray(b"foo")))
    def test_can_send_objects_with_files(self, httpbin, files):
        data = {"a": "this is a string"}
        files = {"b": files}
        r = requests.Request("POST", httpbin("post"), data=data, files=files)
        assert "multipart/form-data" in r.headers["Content-Type"]

    @pytest.mark.xfail(
        reason=(
            "Disallowed via HTTPX using pathlib.Path. Probably not something we "
            "should support."
        ),
        raises=TypeError,
    )
    def test_can_send_file_object_with_non_string_filename(self, httpbin):
        f = io.BytesIO()
        f.name = 2
        r = requests.Request("POST", httpbin("post"), files={"f": f})

        assert "multipart/form-data" in r.headers["Content-Type"]

    def test_autoset_header_values_are_native(self, httpbin):
        data = "this is a string"
        length = "16"
        req = requests.Request("POST", httpbin("post"), data=data)
        assert req.headers["Content-Length"] == length

    @pytest.mark.httpx_bug
    @pytest.mark.xfail(
        reason="HTTPX disallows non-HTTP schemes. Probably a bug?", raises=InvalidURL
    )
    def test_nonhttp_schemes_dont_check_URLs(self):
        test_urls = (
            "data:image/gif;base64,R0lGODlhAQABAHAAACH5BAUAAAAALAAAAAABAAEAAAICRAEAOw==",
            "file:///etc/passwd",
            "magnet:?xt=urn:btih:be08f00302bc2d1d3cfa3af02024fa647a271431",
        )
        for test_url in test_urls:
            req = requests.Request("GET", test_url)
            assert test_url == req.url

    def test_auth_is_stripped_on_http_downgrade(
        self, httpbin, httpbin_secure, httpbin_ca_bundle
    ):
        r = requests.get(
            httpbin_secure("redirect-to"),
            params={"url": httpbin("get")},
            auth=("user", "pass"),
            verify=httpbin_ca_bundle,
        )
        assert r.history[0].request.headers["Authorization"]
        assert "Authorization" not in r.request.headers

    def test_auth_is_retained_for_redirect_on_host(self, httpbin):
        r = requests.get(httpbin("redirect/1"), auth=("user", "pass"))
        h1 = r.history[0].request.headers["Authorization"]
        h2 = r.request.headers["Authorization"]

        assert h1 == h2

    @pytest.mark.xfail(
        reason=(
            "'.should_strip_auth()' doesn't exist in HTTPX, and this seems like a "
            "semi-private API anyways."
        )
    )
    def test_should_strip_auth_host_change(self):
        s = requests.Session()
        assert s.should_strip_auth(
            "http://example.com/foo", "http://another.example.com/"
        )

    @pytest.mark.xfail(
        reason=(
            "'.should_strip_auth()' doesn't exist in HTTPX, and this seems like a "
            "semi-private API anyways."
        )
    )
    def test_should_strip_auth_http_downgrade(self):
        s = requests.Session()
        assert s.should_strip_auth("https://example.com/foo", "http://example.com/bar")

    @pytest.mark.xfail(
        reason=(
            "'.should_strip_auth()' doesn't exist in HTTPX, and this seems like a "
            "semi-private API anyways."
        )
    )
    def test_should_strip_auth_https_upgrade(self):
        s = requests.Session()
        assert not s.should_strip_auth(
            "http://example.com/foo", "https://example.com/bar"
        )
        assert not s.should_strip_auth(
            "http://example.com:80/foo", "https://example.com/bar"
        )
        assert not s.should_strip_auth(
            "http://example.com/foo", "https://example.com:443/bar"
        )
        # Non-standard ports should trigger stripping
        assert s.should_strip_auth(
            "http://example.com:8080/foo", "https://example.com/bar"
        )
        assert s.should_strip_auth(
            "http://example.com/foo", "https://example.com:8443/bar"
        )

    @pytest.mark.xfail(
        reason=(
            "'.should_strip_auth()' doesn't exist in HTTPX, and this seems like a "
            "semi-private API anyways."
        )
    )
    def test_should_strip_auth_port_change(self):
        s = requests.Session()
        assert s.should_strip_auth(
            "http://example.com:1234/foo", "https://example.com:4321/bar"
        )

    @pytest.mark.xfail(
        reason=(
            "'.should_strip_auth()' doesn't exist in HTTPX, and this seems like a "
            "semi-private API anyways."
        )
    )
    @pytest.mark.parametrize(
        "old_uri, new_uri",
        (
            ("https://example.com:443/foo", "https://example.com/bar"),
            ("http://example.com:80/foo", "http://example.com/bar"),
            ("https://example.com/foo", "https://example.com:443/bar"),
            ("http://example.com/foo", "http://example.com:80/bar"),
        ),
    )
    def test_should_strip_auth_default_port(self, old_uri, new_uri):
        s = requests.Session()
        assert not s.should_strip_auth(old_uri, new_uri)

    @pytest.mark.xfail(reason="HTTPX sync responses aren't iterable")
    def test_manual_redirect_with_partial_body_read(self, httpbin):
        s = requests.Session()
        r1 = s.get(httpbin("redirect/2"), allow_redirects=False, stream=True)
        assert r1.is_redirect
        rg = s.resolve_redirects(r1, r1.request, stream=True)

        # read only the first eight bytes of the response body,
        # then follow the redirect
        r1.iter_content(8)
        r2 = next(rg)
        assert r2.is_redirect

        # read all of the response via iter_content,
        # then follow the redirect
        for _ in r2.iter_content():
            pass
        r3 = next(rg)
        assert not r3.is_redirect

    @pytest.mark.skip("Private API")
    def test_prepare_body_position_non_stream(self):
        data = b"the data"
        req = requests.Request("GET", "http://example.com", data=data)
        assert req._body_position is None

    @pytest.mark.skip("HTTPX doesn't have a 'rewind_body' utility")
    def test_rewind_body(self):
        data = io.BytesIO(b"the data")
        prep = requests.Request("GET", "http://example.com", data=data).prepare()
        assert prep._body_position == 0
        assert prep.body.read() == b"the data"

        # the data has all been read
        assert prep.body.read() == b""

        # rewind it back
        requests.utils.rewind_body(prep)
        assert prep.body.read() == b"the data"

    @pytest.mark.skip("HTTPX doesn't have a 'rewind_body' utility")
    def test_rewind_partially_read_body(self):
        data = io.BytesIO(b"the data")
        data.read(4)  # read some data
        prep = requests.Request("GET", "http://example.com", data=data).prepare()
        assert prep._body_position == 4
        assert prep.body.read() == b"data"

        # the data has all been read
        assert prep.body.read() == b""

        # rewind it back
        requests.utils.rewind_body(prep)
        assert prep.body.read() == b"data"

    @pytest.mark.skip("HTTPX doesn't have a 'rewind_body' utility")
    def test_rewind_body_no_seek(self):
        class BadFileObj:
            def __init__(self, data):
                self.data = data

            def tell(self):
                return 0

            def __iter__(self):
                return

        data = BadFileObj("the data")
        prep = requests.Request("GET", "http://example.com", data=data).prepare()
        assert prep._body_position == 0

        with pytest.raises(UnrewindableBodyError) as e:
            requests.utils.rewind_body(prep)

        assert "Unable to rewind request body" in str(e)

    @pytest.mark.skip("HTTPX doesn't have a 'rewind_body' utility")
    def test_rewind_body_failed_seek(self):
        class BadFileObj:
            def __init__(self, data):
                self.data = data

            def tell(self):
                return 0

            def seek(self, pos, whence=0):
                raise OSError()

            def __iter__(self):
                return

        data = BadFileObj("the data")
        prep = requests.Request("GET", "http://example.com", data=data).prepare()
        assert prep._body_position == 0

        with pytest.raises(UnrewindableBodyError) as e:
            requests.utils.rewind_body(prep)

        assert "error occurred when rewinding request body" in str(e)

    @pytest.mark.skip("HTTPX doesn't have a 'rewind_body' utility")
    def test_rewind_body_failed_tell(self):
        class BadFileObj:
            def __init__(self, data):
                self.data = data

            def tell(self):
                raise OSError()

            def __iter__(self):
                return

        data = BadFileObj("the data")
        prep = requests.Request("GET", "http://example.com", data=data).prepare()
        assert prep._body_position is not None

        with pytest.raises(UnrewindableBodyError) as e:
            requests.utils.rewind_body(prep)

        assert "Unable to rewind request body" in str(e)

    def _patch_adapter_gzipped_redirect(self, session, url):
        adapter = session.get_adapter(url=url)
        org_build_response = adapter.build_response
        self._patched_response = False

        def build_response(*args, **kwargs):
            resp = org_build_response(*args, **kwargs)
            if not self._patched_response:
                resp.raw.headers["content-encoding"] = "gzip"
                self._patched_response = True
            return resp

        adapter.build_response = build_response

    @pytest.mark.skip("Private API + no concept of adapter + no assertion made")
    def test_redirect_with_wrong_gzipped_header(self, httpbin):
        s = requests.Session()
        url = httpbin("redirect/1")
        self._patch_adapter_gzipped_redirect(s, url)
        s.get(url)

    @pytest.mark.parametrize(
        "username, password, auth_str",
        (
            ("test", "test", "Basic dGVzdDp0ZXN0"),
            (
                "имя".encode("utf-8"),
                "пароль".encode("utf-8"),
                "Basic 0LjQvNGPOtC/0LDRgNC+0LvRjA==",
            ),
        ),
    )
    def test_basic_auth_str_is_always_native(self, username, password, auth_str):
        s = build_basic_auth_header(username, password)
        assert isinstance(s, str)
        assert s == auth_str

    def test_requests_history_is_saved(self, httpbin):
        r = requests.get(httpbin("redirect/5"))
        total = r.history[-1].history
        i = 0
        for item in r.history:
            assert item.history == total[0:i]
            i += 1

    def test_json_param_post_content_type_works(self, httpbin):
        r = requests.post(httpbin("post"), json={"life": 42})
        assert r.status_code == 200
        assert "application/json" in r.request.headers["Content-Type"]
        assert {"life": 42} == r.json()["json"]

    @pytest.mark.xfail(
        reason=(
            "JSON overrides data param in HTTPX. "
            "The situation is ambiguous: we should probably disallow it."
        )
    )
    def test_json_param_post_should_not_override_data_param(self, httpbin):
        r = requests.Request(
            method="POST",
            url=httpbin("post"),
            data={"stuff": "elixr"},
            json={"music": "flute"},
        )
        assert b"stuff=elixr" == r.content

    @pytest.mark.xfail(
        reason="HTTPX sync responses aren't iterable", raises=AttributeError
    )
    def test_response_iter_lines(self, httpbin):
        r = requests.get(httpbin("stream/4"), stream=True)
        assert r.status_code == 200

        it = r.iter_lines()
        next(it)
        assert len(list(it)) == 3

    @pytest.mark.xfail(
        reason="HTTPX sync responses aren't context managers", raises=AttributeError
    )
    def test_response_context_manager(self, httpbin):
        with requests.get(httpbin("stream/4"), stream=True) as response:
            assert isinstance(response, requests.Response)

        assert response.raw.closed

    @pytest.mark.xfail(
        reason=(
            "HTTPX sync responses aren't context managers. "
            "Note that this would translate as a test on Client instead."
        ),
        raises=AttributeError,
    )
    def test_unconsumed_session_response_closes_connection(self, httpbin):
        s = requests.session()

        with contextlib.closing(s.get(httpbin("stream/4"), stream=True)) as response:
            pass

        assert response._content_consumed is False
        assert response.raw.closed

    @pytest.mark.xfail(reason="Already xfailed by Requests")
    def test_response_iter_lines_reentrant(self, httpbin):
        """Response.iter_lines() is not reentrant safe"""
        r = requests.get(httpbin("stream/4"), stream=True)
        assert r.status_code == 200

        next(r.iter_lines())
        assert len(list(r.iter_lines())) == 3

    @pytest.mark.xfail(reason="Proxies not implemented yet")
    def test_session_close_proxy_clear(self, mocker):
        proxies = {"one": mocker.Mock(), "two": mocker.Mock()}
        session = requests.Session()
        mocker.patch.dict(session.adapters["http://"].proxy_manager, proxies)
        session.close()
        proxies["one"].clear.assert_called_once_with()
        proxies["two"].clear.assert_called_once_with()

    @pytest.mark.xfail(reason="Proxies not implemented yet")
    def test_proxy_auth(self):
        adapter = HTTPAdapter()
        headers = adapter.proxy_headers("http://user:pass@httpbin.org")
        assert headers == {"Proxy-Authorization": "Basic dXNlcjpwYXNz"}

    @pytest.mark.xfail(reason="Proxies not implemented yet")
    def test_proxy_auth_empty_pass(self):
        adapter = HTTPAdapter()
        headers = adapter.proxy_headers("http://user:@httpbin.org")
        assert headers == {"Proxy-Authorization": "Basic dXNlcjo="}

    @pytest.mark.xfail(reason="HTTPX represents empty content with b''")
    def test_response_json_when_content_is_None(self, httpbin):
        r = requests.get(httpbin("/status/204"))
        assert r.content is None
        with pytest.raises(ValueError):
            r.json()

    @pytest.mark.skip(reason="Too specific and irrelevant for HTTPX")
    def test_response_without_release_conn(self):
        """Test `close` call for non-urllib3-like raw objects.
        Should work when `release_conn` attr doesn't exist on `response.raw`.
        """
        resp = requests.Response()
        resp.raw = StringIO.StringIO("test")
        assert not resp.raw.closed
        resp.close()
        assert resp.raw.closed

    def test_empty_stream_with_auth_does_not_set_content_length_header(self, httpbin):
        """Ensure that a byte stream with size 0 will not set both a Content-Length
        and Transfer-Encoding header.
        """
        auth = ("user", "pass")
        url = httpbin("post")
        file_obj = io.BytesIO(b"")
        resp = requests.request("POST", url, auth=auth, data=file_obj)
        r = resp.request
        assert "Transfer-Encoding" in r.headers
        assert "Content-Length" not in r.headers

    @pytest.mark.xfail(
        reason=("Transfer-Encoding is present. Not sure if this is a bug.")
    )
    def test_stream_with_auth_does_not_set_transfer_encoding_header(self, httpbin):
        """Ensure that a byte stream with size > 0 will not set both a Content-Length
        and Transfer-Encoding header.
        """
        auth = ("user", "pass")
        url = httpbin("post")
        file_obj = io.BytesIO(b"test data")
        resp = requests.request("POST", url, auth=auth, data=file_obj)
        file_obj.close()
        r = resp.request
        assert "Transfer-Encoding" not in r.headers
        assert "Content-Length" in r.headers

    @pytest.mark.xfail(
        reason=(
            "This test is flaky - maybe a sign that the handling of "
            "generator request body needs fine-tuning?"
        )
    )
    def test_chunked_upload_does_not_set_content_length_header(self, httpbin):
        """Ensure that requests with a generator body stream using
        Transfer-Encoding: chunked, not a Content-Length header.
        """
        data = (i for i in [b"a", b"b", b"c"])
        url = httpbin("post")
        resp = requests.request("POST", url, data=data)
        r = resp.request
        assert "Transfer-Encoding" in r.headers
        assert "Content-Length" not in r.headers

    @pytest.mark.xfail(reason="Not implemented in HTTPX (not this way, at least)")
    def test_custom_redirect_mixin(self, httpbin):
        """Tests a custom mixin to overwrite ``get_redirect_target``.

        Ensures a subclassed ``requests.Session`` can handle a certain type of
        malformed redirect responses.

        1. original request receives a proper response: 302 redirect
        2. following the redirect, a malformed response is given:
            status code = HTTP 200
            location = alternate url
        3. the custom session catches the edge case and follows the redirect
        """
        url_final = httpbin("html")
        querystring_malformed = urlencode({"location": url_final})
        url_redirect_malformed = httpbin("response-headers?%s" % querystring_malformed)
        querystring_redirect = urlencode({"url": url_redirect_malformed})
        url_redirect = httpbin("redirect-to?%s" % querystring_redirect)
        urls_test = [url_redirect, url_redirect_malformed, url_final]

        class CustomRedirectSession(requests.Session):
            def get_redirect_target(self, resp):
                # default behavior
                if resp.is_redirect:
                    return resp.headers["location"]
                # edge case - check to see if 'location' is in headers anyways
                location = resp.headers.get("location")
                if location and (location != resp.url):
                    return location
                return None

        session = CustomRedirectSession()
        r = session.get(urls_test[0])
        assert len(r.history) == 2
        assert r.status_code == 200
        assert r.history[0].status_code == 302
        assert r.history[0].is_redirect
        assert r.history[1].status_code == 200
        assert not r.history[1].is_redirect
        assert r.url == urls_test[2]
