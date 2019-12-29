import json
from http.cookiejar import Cookie, CookieJar

import pytest

from httpx import Client, Cookies, Request, Response
from httpx.config import CertTypes, TimeoutTypes, VerifyTypes
from httpx.dispatch.base import Dispatcher


class MockDispatch(Dispatcher):
    async def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        if request.url.path.startswith("/echo_cookies"):
            body = json.dumps({"cookies": request.headers.get("Cookie")}).encode()
            return Response(200, content=body, request=request)
        elif request.url.path.startswith("/set_cookie"):
            headers = {"set-cookie": "example-name=example-value"}
            return Response(200, headers=headers, request=request)
        else:
            raise NotImplementedError  # pragma: no cover


@pytest.mark.asyncio
async def test_set_cookie() -> None:
    """
    Send a request including a cookie.
    """
    url = "http://example.org/echo_cookies"
    cookies = {"example-name": "example-value"}

    client = Client(dispatch=MockDispatch())
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

    client = Client(dispatch=MockDispatch())
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

    client = Client(dispatch=MockDispatch())
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

    client = Client(dispatch=MockDispatch())
    response = await client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


@pytest.mark.asyncio
async def test_get_cookie() -> None:
    url = "http://example.org/set_cookie"

    client = Client(dispatch=MockDispatch())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.cookies["example-name"] == "example-value"
    assert client.cookies["example-name"] == "example-value"


@pytest.mark.asyncio
async def test_cookie_persistence() -> None:
    """
    Ensure that Client instances persist cookies between requests.
    """
    client = Client(dispatch=MockDispatch())

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
