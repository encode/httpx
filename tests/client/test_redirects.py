import json
import typing
from urllib.parse import parse_qs

import pytest

from httpx import (
    URL,
    AsyncClient,
    NotRedirectResponse,
    RedirectLoop,
    RequestBodyUnavailable,
    TooManyRedirects,
    codes,
)
from httpx._config import TimeoutTypes
from httpx._content_streams import AsyncIteratorStream, ByteStream, ContentStream
from httpx._dispatch.base import AsyncDispatcher


def get_header_value(headers, key, default=None):
    lookup = key.encode("ascii").lower()
    for header_key, header_value in headers:
        if header_key.lower() == lookup:
            return header_value.decode("ascii")
    return default


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        method: bytes,
        url: URL,
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: TimeoutTypes = None,
    ) -> typing.Tuple[int, str, typing.List[typing.Tuple[bytes, bytes]], ContentStream]:
        if url.path == "/no_redirect":
            return codes.OK, "HTTP/1.1", [], ByteStream(b"")

        elif url.path == "/redirect_301":

            async def body():
                yield b"<a href='https://example.org/'>here</a>"

            status_code = codes.MOVED_PERMANENTLY
            headers = [(b"location", b"https://example.org/")]
            stream = AsyncIteratorStream(aiterator=body())
            return status_code, "HTTP/1.1", headers, stream

        elif url.path == "/redirect_302":
            status_code = codes.FOUND
            headers = [(b"location", b"https://example.org/")]
            return status_code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/redirect_303":
            status_code = codes.SEE_OTHER
            headers = [(b"location", b"https://example.org/")]
            return status_code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/relative_redirect":
            status_code = codes.SEE_OTHER
            headers = [(b"location", b"/")]
            return status_code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/malformed_redirect":
            status_code = codes.SEE_OTHER
            headers = [(b"location", b"https://:443/")]
            return status_code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/no_scheme_redirect":
            status_code = codes.SEE_OTHER
            headers = [(b"location", b"//example.org/")]
            return status_code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/multiple_redirects":
            params = parse_qs(url.query)
            count = int(params.get("count", "0")[0])
            redirect_count = count - 1
            code = codes.SEE_OTHER if count else codes.OK
            location = b"/multiple_redirects"
            if redirect_count:
                location += b"?count=" + str(redirect_count).encode("ascii")
            headers = [(b"location", location)] if count else []
            return code, "HTTP/1.1", headers, ByteStream(b"")

        if url.path == "/redirect_loop":
            code = codes.SEE_OTHER
            headers = [(b"location", b"/redirect_loop")]
            return code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/cross_domain":
            code = codes.SEE_OTHER
            headers = [(b"location", b"https://example.org/cross_domain_target")]
            return code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/cross_domain_target":
            headers_dict = dict(
                [(key.decode("ascii"), value.decode("ascii")) for key, value in headers]
            )
            content = ByteStream(json.dumps({"headers": headers_dict}).encode())
            return 200, "HTTP/1.1", [], content

        elif url.path == "/redirect_body":
            _ = b"".join([part async for part in stream])
            code = codes.PERMANENT_REDIRECT
            headers = [(b"location", b"/redirect_body_target")]
            return code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/redirect_no_body":
            _ = b"".join([part async for part in stream])
            code = codes.SEE_OTHER
            headers = [(b"location", b"/redirect_body_target")]
            return code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/redirect_body_target":
            content = b"".join([part async for part in stream])
            headers_dict = dict(
                [(key.decode("ascii"), value.decode("ascii")) for key, value in headers]
            )
            body = ByteStream(
                json.dumps({"body": content.decode(), "headers": headers_dict}).encode()
            )
            return 200, "HTTP/1.1", [], body

        elif url.path == "/cross_subdomain":
            host = get_header_value(headers, "host")
            if host != "www.example.org":
                headers = [(b"location", b"https://www.example.org/cross_subdomain")]
                return codes.PERMANENT_REDIRECT, "HTTP/1.1", headers, ByteStream(b"")
            else:
                return 200, "HTTP/1.1", [], ByteStream(b"Hello, world!")

        return 200, "HTTP/1.1", [], ByteStream(b"Hello, world!")


@pytest.mark.usefixtures("async_environment")
async def test_no_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.com/no_redirect"
    response = await client.get(url)
    assert response.status_code == 200
    with pytest.raises(NotRedirectResponse):
        await response.anext()


@pytest.mark.usefixtures("async_environment")
async def test_redirect_301():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.post("https://example.org/redirect_301")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_redirect_302():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.post("https://example.org/redirect_302")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_redirect_303():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get("https://example.org/redirect_303")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_disallow_redirects():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.post(
        "https://example.org/redirect_303", allow_redirects=False
    )
    assert response.status_code == codes.SEE_OTHER
    assert response.url == URL("https://example.org/redirect_303")
    assert response.is_redirect is True
    assert len(response.history) == 0

    response = await response.anext()
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert response.is_redirect is False
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_relative_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get("https://example.org/relative_redirect")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_malformed_redirect():
    # https://github.com/encode/httpx/issues/771
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get("http://example.org/malformed_redirect")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_no_scheme_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get("https://example.org/no_scheme_redirect")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_fragment_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get("https://example.org/relative_redirect#fragment")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/#fragment")
    assert len(response.history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_multiple_redirects():
    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get("https://example.org/multiple_redirects?count=20")
    assert response.status_code == codes.OK
    assert response.url == URL("https://example.org/multiple_redirects")
    assert len(response.history) == 20
    assert response.history[0].url == URL(
        "https://example.org/multiple_redirects?count=20"
    )
    assert response.history[1].url == URL(
        "https://example.org/multiple_redirects?count=19"
    )
    assert len(response.history[0].history) == 0
    assert len(response.history[1].history) == 1


@pytest.mark.usefixtures("async_environment")
async def test_too_many_redirects():
    client = AsyncClient(dispatch=MockDispatch())
    with pytest.raises(TooManyRedirects):
        await client.get("https://example.org/multiple_redirects?count=21")


@pytest.mark.usefixtures("async_environment")
async def test_too_many_redirects_calling_next():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/multiple_redirects?count=21"
    response = await client.get(url, allow_redirects=False)
    with pytest.raises(TooManyRedirects):
        while response.is_redirect:
            response = await response.anext()


@pytest.mark.usefixtures("async_environment")
async def test_redirect_loop():
    client = AsyncClient(dispatch=MockDispatch())
    with pytest.raises(RedirectLoop):
        await client.get("https://example.org/redirect_loop")


@pytest.mark.usefixtures("async_environment")
async def test_redirect_loop_calling_next():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/redirect_loop"
    response = await client.get(url, allow_redirects=False)
    with pytest.raises(RedirectLoop):
        while response.is_redirect:
            response = await response.anext()


@pytest.mark.usefixtures("async_environment")
async def test_cross_domain_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.com/cross_domain"
    headers = {"Authorization": "abc"}
    response = await client.get(url, headers=headers)
    assert response.url == URL("https://example.org/cross_domain_target")
    assert "authorization" not in response.json()["headers"]


@pytest.mark.usefixtures("async_environment")
async def test_same_domain_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/cross_domain"
    headers = {"Authorization": "abc"}
    response = await client.get(url, headers=headers)
    assert response.url == URL("https://example.org/cross_domain_target")
    assert response.json()["headers"]["authorization"] == "abc"


@pytest.mark.usefixtures("async_environment")
async def test_body_redirect():
    """
    A 308 redirect should preserve the request body.
    """
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/redirect_body"
    data = b"Example request body"
    response = await client.post(url, data=data)
    assert response.url == URL("https://example.org/redirect_body_target")
    assert response.json()["body"] == "Example request body"
    assert "content-length" in response.json()["headers"]


@pytest.mark.usefixtures("async_environment")
async def test_no_body_redirect():
    """
    A 303 redirect should remove the request body.
    """
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/redirect_no_body"
    data = b"Example request body"
    response = await client.post(url, data=data)
    assert response.url == URL("https://example.org/redirect_body_target")
    assert response.json()["body"] == ""
    assert "content-length" not in response.json()["headers"]


@pytest.mark.usefixtures("async_environment")
async def test_can_stream_if_no_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/redirect_301"
    async with client.stream("GET", url, allow_redirects=False) as response:
        assert not response.is_closed
    assert response.status_code == codes.MOVED_PERMANENTLY
    assert response.headers["location"] == "https://example.org/"


@pytest.mark.usefixtures("async_environment")
async def test_cannot_redirect_streaming_body():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.org/redirect_body"

    async def streaming_body():
        yield b"Example request body"

    with pytest.raises(RequestBodyUnavailable):
        await client.post(url, data=streaming_body())


@pytest.mark.usefixtures("async_environment")
async def test_cross_subdomain_redirect():
    client = AsyncClient(dispatch=MockDispatch())
    url = "https://example.com/cross_subdomain"
    response = await client.get(url)
    assert response.url == URL("https://www.example.org/cross_subdomain")


class MockCookieDispatch(AsyncDispatcher):
    async def send(
        self,
        method: bytes,
        url: URL,
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: TimeoutTypes = None,
    ) -> typing.Tuple[int, str, typing.List[typing.Tuple[bytes, bytes]], ContentStream]:
        if url.path == "/":
            cookie = get_header_value(headers, "Cookie")
            if cookie is not None:
                content = b"Logged in"
            else:
                content = b"Not logged in"
            return 200, "HTTP/1.1", [], ByteStream(content)

        elif url.path == "/login":
            status_code = codes.SEE_OTHER
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
            return status_code, "HTTP/1.1", headers, ByteStream(b"")

        elif url.path == "/logout":
            status_code = codes.SEE_OTHER
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
            return status_code, "HTTP/1.1", headers, ByteStream(b"")


@pytest.mark.usefixtures("async_environment")
async def test_redirect_cookie_behavior():
    client = AsyncClient(dispatch=MockCookieDispatch())

    # The client is not logged in.
    response = await client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"

    # Login redirects to the homepage, setting a session cookie.
    response = await client.post("https://example.com/login")
    assert response.url == "https://example.com/"
    assert response.text == "Logged in"

    # The client is logged in.
    response = await client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Logged in"

    # Logout redirects to the homepage, expiring the session cookie.
    response = await client.post("https://example.com/logout")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"

    # The client is not logged in.
    response = await client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"
