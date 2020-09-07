import json
import typing
from urllib.parse import parse_qs

import httpcore
import pytest

import httpx
from httpx._content_streams import ByteStream, ContentStream, IteratorStream


def get_header_value(headers, key, default=None):
    lookup = key.encode("ascii").lower()
    for header_key, header_value in headers:
        if header_key.lower() == lookup:
            return header_value.decode("ascii")
    return default


class MockTransport:
    def _request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, int, bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: typing.Mapping[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        scheme, host, port, path = url
        if scheme not in (b"http", b"https"):
            raise httpcore.UnsupportedProtocol(f"Scheme {scheme!r} not supported.")

        path, _, query = path.partition(b"?")
        if path == b"/no_redirect":
            return b"HTTP/1.1", httpx.codes.OK, b"OK", [], ByteStream(b"")

        elif path == b"/redirect_301":

            def body():
                yield b"<a href='https://example.org/'>here</a>"

            status_code = httpx.codes.MOVED_PERMANENTLY
            headers = [(b"location", b"https://example.org/")]
            stream = IteratorStream(iterator=body())
            return b"HTTP/1.1", status_code, b"Moved Permanently", headers, stream

        elif path == b"/redirect_302":
            status_code = httpx.codes.FOUND
            headers = [(b"location", b"https://example.org/")]
            return b"HTTP/1.1", status_code, b"Found", headers, ByteStream(b"")

        elif path == b"/redirect_303":
            status_code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"https://example.org/")]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")

        elif path == b"/relative_redirect":
            status_code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"/")]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")

        elif path == b"/malformed_redirect":
            status_code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"https://:443/")]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")

        elif path == b"/invalid_redirect":
            status_code = httpx.codes.SEE_OTHER
            headers = [(b"location", "https://😇/".encode("utf-8"))]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")

        elif path == b"/no_scheme_redirect":
            status_code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"//example.org/")]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")

        elif path == b"/multiple_redirects":
            params = parse_qs(query.decode("ascii"))
            count = int(params.get("count", "0")[0])
            redirect_count = count - 1
            code = httpx.codes.SEE_OTHER if count else httpx.codes.OK
            phrase = b"See Other" if count else b"OK"
            location = b"/multiple_redirects"
            if redirect_count:
                location += b"?count=" + str(redirect_count).encode("ascii")
            headers = [(b"location", location)] if count else []
            return b"HTTP/1.1", code, phrase, headers, ByteStream(b"")

        if path == b"/redirect_loop":
            code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"/redirect_loop")]
            return b"HTTP/1.1", code, b"See Other", headers, ByteStream(b"")

        elif path == b"/cross_domain":
            code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"https://example.org/cross_domain_target")]
            return b"HTTP/1.1", code, b"See Other", headers, ByteStream(b"")

        elif path == b"/cross_domain_target":
            headers_dict = {
                key.decode("ascii"): value.decode("ascii") for key, value in headers
            }
            stream = ByteStream(json.dumps({"headers": headers_dict}).encode())
            return b"HTTP/1.1", 200, b"OK", [], stream

        elif path == b"/redirect_body":
            code = httpx.codes.PERMANENT_REDIRECT
            headers = [(b"location", b"/redirect_body_target")]
            return b"HTTP/1.1", code, b"Permanent Redirect", headers, ByteStream(b"")

        elif path == b"/redirect_no_body":
            code = httpx.codes.SEE_OTHER
            headers = [(b"location", b"/redirect_body_target")]
            return b"HTTP/1.1", code, b"See Other", headers, ByteStream(b"")

        elif path == b"/redirect_body_target":
            content = b"".join(stream)
            headers_dict = {
                key.decode("ascii"): value.decode("ascii") for key, value in headers
            }
            stream = ByteStream(
                json.dumps({"body": content.decode(), "headers": headers_dict}).encode()
            )
            return b"HTTP/1.1", 200, b"OK", [], stream

        elif path == b"/cross_subdomain":
            host = get_header_value(headers, "host")
            if host != "www.example.org":
                headers = [(b"location", b"https://www.example.org/cross_subdomain")]
                return (
                    b"HTTP/1.1",
                    httpx.codes.PERMANENT_REDIRECT,
                    b"Permanent Redirect",
                    headers,
                    ByteStream(b""),
                )
            else:
                return b"HTTP/1.1", 200, b"OK", [], ByteStream(b"Hello, world!")

        elif path == b"/redirect_custom_scheme":
            status_code = httpx.codes.MOVED_PERMANENTLY
            headers = [(b"location", b"market://details?id=42")]
            return (
                b"HTTP/1.1",
                status_code,
                b"Moved Permanently",
                headers,
                ByteStream(b""),
            )

        stream = ByteStream(b"Hello, world!") if method != b"HEAD" else ByteStream(b"")

        return b"HTTP/1.1", 200, b"OK", [], stream


class AsyncMockTransport(MockTransport, httpcore.AsyncHTTPTransport):
    async def request(
        self, *args, **kwargs
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        return self._request(*args, **kwargs)


class SyncMockTransport(MockTransport, httpcore.SyncHTTPTransport):
    def request(
        self, *args, **kwargs
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        return self._request(*args, **kwargs)


def test_no_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.com/no_redirect"
    response = client.get(url)
    assert response.status_code == 200
    with pytest.raises(httpx.NotRedirectResponse):
        response.next()


def test_redirect_301():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.post("https://example.org/redirect_301")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_redirect_302():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.post("https://example.org/redirect_302")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_redirect_303():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.get("https://example.org/redirect_303")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_disallow_redirects():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.post("https://example.org/redirect_303", allow_redirects=False)
    assert response.status_code == httpx.codes.SEE_OTHER
    assert response.url == "https://example.org/redirect_303"
    assert response.is_redirect is True
    assert len(response.history) == 0

    response = response.next()
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert response.is_redirect is False
    assert len(response.history) == 1


def test_head_redirect():
    """
    Contrary to Requests, redirects remain enabled by default for HEAD requests.
    """
    client = httpx.Client(transport=SyncMockTransport())
    response = client.head("https://example.org/redirect_302")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert response.request.method == "HEAD"
    assert len(response.history) == 1
    assert response.text == ""


def test_relative_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.get("https://example.org/relative_redirect")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_malformed_redirect():
    # https://github.com/encode/httpx/issues/771
    client = httpx.Client(transport=SyncMockTransport())
    response = client.get("http://example.org/malformed_redirect")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org:443/"
    assert len(response.history) == 1


def test_invalid_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    with pytest.raises(httpx.RemoteProtocolError):
        client.get("http://example.org/invalid_redirect")


def test_no_scheme_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.get("https://example.org/no_scheme_redirect")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_fragment_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.get("https://example.org/relative_redirect#fragment")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/#fragment"
    assert len(response.history) == 1


def test_multiple_redirects():
    client = httpx.Client(transport=SyncMockTransport())
    response = client.get("https://example.org/multiple_redirects?count=20")
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/multiple_redirects"
    assert len(response.history) == 20
    assert response.history[0].url == "https://example.org/multiple_redirects?count=20"
    assert response.history[1].url == "https://example.org/multiple_redirects?count=19"
    assert len(response.history[0].history) == 0
    assert len(response.history[1].history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_async_too_many_redirects():
    async with httpx.AsyncClient(transport=AsyncMockTransport()) as client:
        with pytest.raises(httpx.TooManyRedirects):
            await client.get("https://example.org/multiple_redirects?count=21")


@pytest.mark.usefixtures("async_environment")
async def test_async_too_many_redirects_calling_next():
    async with httpx.AsyncClient(transport=AsyncMockTransport()) as client:
        url = "https://example.org/multiple_redirects?count=21"
        response = await client.get(url, allow_redirects=False)
        with pytest.raises(httpx.TooManyRedirects):
            while response.is_redirect:
                response = await response.anext()


def test_sync_too_many_redirects():
    client = httpx.Client(transport=SyncMockTransport())
    with pytest.raises(httpx.TooManyRedirects):
        client.get("https://example.org/multiple_redirects?count=21")


def test_sync_too_many_redirects_calling_next():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.org/multiple_redirects?count=21"
    response = client.get(url, allow_redirects=False)
    with pytest.raises(httpx.TooManyRedirects):
        while response.is_redirect:
            response = response.next()


def test_redirect_loop():
    client = httpx.Client(transport=SyncMockTransport())
    with pytest.raises(httpx.TooManyRedirects):
        client.get("https://example.org/redirect_loop")


def test_cross_domain_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.com/cross_domain"
    headers = {"Authorization": "abc"}
    response = client.get(url, headers=headers)
    assert response.url == "https://example.org/cross_domain_target"
    assert "authorization" not in response.json()["headers"]


def test_same_domain_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.org/cross_domain"
    headers = {"Authorization": "abc"}
    response = client.get(url, headers=headers)
    assert response.url == "https://example.org/cross_domain_target"
    assert response.json()["headers"]["authorization"] == "abc"


def test_body_redirect():
    """
    A 308 redirect should preserve the request body.
    """
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.org/redirect_body"
    content = b"Example request body"
    response = client.post(url, content=content)
    assert response.url == "https://example.org/redirect_body_target"
    assert response.json()["body"] == "Example request body"
    assert "content-length" in response.json()["headers"]


def test_no_body_redirect():
    """
    A 303 redirect should remove the request body.
    """
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.org/redirect_no_body"
    content = b"Example request body"
    response = client.post(url, content=content)
    assert response.url == "https://example.org/redirect_body_target"
    assert response.json()["body"] == ""
    assert "content-length" not in response.json()["headers"]


def test_can_stream_if_no_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.org/redirect_301"
    with client.stream("GET", url, allow_redirects=False) as response:
        assert not response.is_closed
    assert response.status_code == httpx.codes.MOVED_PERMANENTLY
    assert response.headers["location"] == "https://example.org/"


def test_cannot_redirect_streaming_body():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.org/redirect_body"

    def streaming_body():
        yield b"Example request body"  # pragma: nocover

    with pytest.raises(httpx.RequestBodyUnavailable):
        client.post(url, content=streaming_body())


def test_cross_subdomain_redirect():
    client = httpx.Client(transport=SyncMockTransport())
    url = "https://example.com/cross_subdomain"
    response = client.get(url)
    assert response.url == "https://www.example.org/cross_subdomain"


class MockCookieTransport(httpcore.SyncHTTPTransport):
    def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        timeout: typing.Mapping[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        scheme, host, port, path = url
        if path == b"/":
            cookie = get_header_value(headers, "Cookie")
            if cookie is not None:
                content = b"Logged in"
            else:
                content = b"Not logged in"
            return b"HTTP/1.1", 200, b"OK", [], ByteStream(content)

        elif path == b"/login":
            status_code = httpx.codes.SEE_OTHER
            headers = [
                (b"location", b"/"),
                (
                    b"set-cookie",
                    (
                        b"session=eyJ1c2VybmFtZSI6ICJ0b21; path=/; Max-Age=1209600; "
                        b"httponly; samesite=lax"
                    ),
                ),
            ]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")

        else:
            assert path == b"/logout"
            status_code = httpx.codes.SEE_OTHER
            headers = [
                (b"location", b"/"),
                (
                    b"set-cookie",
                    (
                        b"session=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; "
                        b"httponly; samesite=lax"
                    ),
                ),
            ]
            return b"HTTP/1.1", status_code, b"See Other", headers, ByteStream(b"")


def test_redirect_cookie_behavior():
    client = httpx.Client(transport=MockCookieTransport())

    # The client is not logged in.
    response = client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"

    # Login redirects to the homepage, setting a session cookie.
    response = client.post("https://example.com/login")
    assert response.url == "https://example.com/"
    assert response.text == "Logged in"

    # The client is logged in.
    response = client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Logged in"

    # Logout redirects to the homepage, expiring the session cookie.
    response = client.post("https://example.com/logout")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"

    # The client is not logged in.
    response = client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"


def test_redirect_custom_scheme():
    client = httpx.Client(transport=SyncMockTransport())
    with pytest.raises(httpx.UnsupportedProtocol) as e:
        client.post("https://example.org/redirect_custom_scheme")
    assert str(e.value) == "Scheme b'market' not supported."
