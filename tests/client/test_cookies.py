import typing
from http.cookiejar import Cookie, CookieJar

import httpcore

import httpx
from httpx._content_streams import ByteStream, ContentStream, JSONStream


def get_header_value(headers, key, default=None):
    lookup = key.encode("ascii").lower()
    for header_key, header_value in headers:
        if header_key.lower() == lookup:
            return header_value.decode("ascii")
    return default


class MockTransport(httpcore.SyncHTTPTransport):
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
        host, scheme, port, path = url
        body: ContentStream
        if path.startswith(b"/echo_cookies"):
            cookie = get_header_value(headers, "cookie")
            body = JSONStream({"cookies": cookie})
            return b"HTTP/1.1", 200, b"OK", [], body
        elif path.startswith(b"/set_cookie"):
            headers = [(b"set-cookie", b"example-name=example-value")]
            body = ByteStream(b"")
            return b"HTTP/1.1", 200, b"OK", headers, body
        else:
            raise NotImplementedError()  # pragma: no cover


def test_set_cookie() -> None:
    """
    Send a request including a cookie.
    """
    url = "http://example.org/echo_cookies"
    cookies = {"example-name": "example-value"}

    client = httpx.Client(transport=MockTransport())
    response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


def test_set_cookie_with_cookiejar() -> None:
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

    client = httpx.Client(transport=MockTransport())
    response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


def test_setting_client_cookies_to_cookiejar() -> None:
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

    client = httpx.Client(transport=MockTransport())
    client.cookies = cookies  # type: ignore
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


def test_set_cookie_with_cookies_model() -> None:
    """
    Send a request including a cookie, using a `Cookies` instance.
    """

    url = "http://example.org/echo_cookies"
    cookies = httpx.Cookies()
    cookies["example-name"] = "example-value"

    client = httpx.Client(transport=MockTransport())
    response = client.get(url, cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"cookies": "example-name=example-value"}


def test_get_cookie() -> None:
    url = "http://example.org/set_cookie"

    client = httpx.Client(transport=MockTransport())
    response = client.get(url)

    assert response.status_code == 200
    assert response.cookies["example-name"] == "example-value"
    assert client.cookies["example-name"] == "example-value"


def test_cookie_persistence() -> None:
    """
    Ensure that Client instances persist cookies between requests.
    """
    client = httpx.Client(transport=MockTransport())

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
