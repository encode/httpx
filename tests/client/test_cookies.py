import typing
from http.cookiejar import Cookie, CookieJar

import pytest

from httpx import URL, AsyncClient, Cookies
from httpx._config import TimeoutTypes
from httpx._content_streams import ByteStream, ContentStream, JSONStream
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
        if url.path.startswith("/echo_cookies"):
            cookie = get_header_value(headers, "cookie")
            body = JSONStream({"cookies": cookie})
            return 200, "HTTP/1.1", [], body
        elif url.path.startswith("/set_cookie"):
            headers = [(b"set-cookie", b"example-name=example-value")]
            body = ByteStream(b"")
            return 200, "HTTP/1.1", headers, body
        else:
            raise NotImplementedError()  # pragma: no cover


@pytest.mark.asyncio
async def test_set_cookie() -> None:
    """
    Send a request including a cookie.
    """
    url = "http://example.org/echo_cookies"
    cookies = {"example-name": "example-value"}

    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


@pytest.mark.asyncio
async def test_set_cookie_with_cookiejar() -> None:
    """
    Send a request including a cookie, using a `CookieJar` instance.
    """

    url = "http://example.org/echo_cookies"
    cookies = CookieJar()
    cookie = Cookie(
        version=0,
        name="example-name",
        value="example-value",
        port=None,
        port_specified=False,
        domain="",
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": ""},
        rfc2109=False,
    )
    cookies.set_cookie(cookie)

    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


@pytest.mark.asyncio
async def test_setting_client_cookies_to_cookiejar() -> None:
    """
    Send a request including a cookie, using a `CookieJar` instance.
    """

    url = "http://example.org/echo_cookies"
    cookies = CookieJar()
    cookie = Cookie(
        version=0,
        name="example-name",
        value="example-value",
        port=None,
        port_specified=False,
        domain="",
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": ""},
        rfc2109=False,
    )
    cookies.set_cookie(cookie)

    client = AsyncClient(dispatch=MockDispatch())
    client.cookies = cookies  # type: ignore
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


@pytest.mark.asyncio
async def test_set_cookie_with_cookies_model() -> None:
    """
    Send a request including a cookie, using a `Cookies` instance.
    """

    url = "http://example.org/echo_cookies"
    cookies = Cookies()
    cookies["example-name"] = "example-value"

    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


@pytest.mark.asyncio
async def test_get_cookie() -> None:
    url = "http://example.org/set_cookie"

    client = AsyncClient(dispatch=MockDispatch())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.cookies["example-name"] == "example-value"
    assert client.cookies["example-name"] == "example-value"


@pytest.mark.asyncio
async def test_cookie_persistence() -> None:
    """
    Ensure that Client instances persist cookies between requests.
    """
    client = AsyncClient(dispatch=MockDispatch())

    response = await client.get("http://example.org/echo_cookies")
    assert response.status_code == 200
    assert response.json() == {"cookies": None}

    response = await client.get("http://example.org/set_cookie")
    assert response.status_code == 200
    assert response.cookies["example-name"] == "example-value"
    assert client.cookies["example-name"] == "example-value"

    response = await client.get("http://example.org/echo_cookies")
    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}
