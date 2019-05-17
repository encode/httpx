import json
from http.cookiejar import Cookie, CookieJar

import pytest

from httpcore import (
    URL,
    Client,
    Cookies,
    Dispatcher,
    Request,
    Response,
    SSLConfig,
    TimeoutConfig,
)


class MockDispatch(Dispatcher):
    async def send(
        self,
        request: Request,
        stream: bool = False,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        if request.url.path.startswith("/echo_cookies"):
            body = json.dumps({"cookies": request.headers.get("Cookie")}).encode()
            return Response(200, content=body, request=request)
        elif request.url.path.startswith("/set_cookie"):
            headers = {"set-cookie": "example-name=example-value"}
            return Response(200, headers=headers, request=request)


def test_set_cookie():
    """
    Send a request including a cookie.
    """
    url = "http://example.org/echo_cookies"
    cookies = {"example-name": "example-value"}

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert json.loads(response.text) == {"cookies": "example-name=example-value"}


def test_set_cookie_with_cookiejar():
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
        rest={"HttpOnly": None},
        rfc2109=False,
    )
    cookies.set_cookie(cookie)

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert json.loads(response.text) == {"cookies": "example-name=example-value"}


def test_set_cookie_with_cookies_model():
    """
    Send a request including a cookie, using a `Cookies` instance.
    """

    url = "http://example.org/echo_cookies"
    cookies = Cookies()
    cookies["example-name"] = "example-value"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert json.loads(response.text) == {"cookies": "example-name=example-value"}


def test_get_cookie():
    url = "http://example.org/set_cookie"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.cookies["example-name"] == "example-value"
