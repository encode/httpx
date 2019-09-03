import json
from http.cookiejar import Cookie, CookieJar

from httpx import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    Cookies,
    TimeoutTypes,
    VerifyTypes,
)


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        if request.url.path.startswith("/echo_cookies"):
            body = json.dumps({"cookies": request.headers.get("Cookie")}).encode()
            return AsyncResponse(200, content=body, request=request)
        elif request.url.path.startswith("/set_cookie"):
            headers = {"set-cookie": "example-name=example-value"}
            return AsyncResponse(200, headers=headers, request=request)


def test_set_cookie():
    """
    Send a request including a cookie.
    """
    url = "http://example.org/echo_cookies"
    cookies = {"example-name": "example-value"}

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


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
    assert response.json() == {"cookies": "example-name=example-value"}


def test_setting_client_cookies_to_cookiejar():
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
        client.cookies = cookies
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


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
    assert response.json() == {"cookies": "example-name=example-value"}


def test_get_cookie():
    url = "http://example.org/set_cookie"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.cookies["example-name"] == "example-value"
    assert client.cookies["example-name"] == "example-value"


def test_cookie_persistence():
    """
    Ensure that Client instances persist cookies between requests.
    """
    with Client(dispatch=MockDispatch()) as client:
        response = client.get("http://example.org/echo_cookies")
        assert response.status_code == 200
        assert response.json() == {"cookies": None}

        response = client.get("http://example.org/set_cookie")
        assert response.status_code == 200
        assert response.cookies["example-name"] == "example-value"
        assert client.cookies["example-name"] == "example-value"

        response = client.get("http://example.org/echo_cookies")
        assert response.status_code == 200
        assert response.json() == {"cookies": "example-name=example-value"}
