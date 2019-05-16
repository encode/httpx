import json
from http.cookiejar import Cookie, CookieJar

import pytest

from httpcore import (
    URL,
    Client,
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
        if request.url.path.startswith('/echo_cookies'):
            body = json.dumps({"cookies": request.headers.get("Cookie")}).encode()
            return Response(200, content=body, request=request)
        elif request.url.path.startswith('/set_cookie'):
            headers = {"set-cookie": "example-name=example-value"}
            return Response(200, headers=headers, request=request)


def create_cookie(name, value, **kwargs):
    result = {
        "version": 0,
        "name": name,
        "value": value,
        "port": None,
        "domain": "",
        "path": "/",
        "secure": False,
        "expires": None,
        "discard": True,
        "comment": None,
        "comment_url": None,
        "rest": {"HttpOnly": None},
        "rfc2109": False,
    }

    result.update(kwargs)
    result["port_specified"] = bool(result["port"])
    result["domain_specified"] = bool(result["domain"])
    result["domain_initial_dot"] = result["domain"].startswith(".")
    result["path_specified"] = bool(result["path"])

    return Cookie(**result)


def test_set_cookie():
    url = "http://example.org/echo_cookies"
    cookie = create_cookie("example-name", "example-value")
    cookies = CookieJar()
    cookies.set_cookie(cookie)

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert json.loads(response.text) == {"cookies": "example-name=example-value"}


def test_get_cookie():
    url = "http://example.org/set_cookie"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    cookies = list(response.cookies)
    assert len(cookies) == 1
    cookie = cookies[0]
    assert cookie.name == "example-name"
    assert cookie.value == "example-value"
