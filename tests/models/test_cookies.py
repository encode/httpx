import http

import pytest

import httpx


def test_cookies():
    cookies = httpx.Cookies({"name": "value"})
    assert cookies["name"] == "value"
    assert "name" in cookies
    assert len(cookies) == 1
    assert dict(cookies) == {"name": "value"}
    assert bool(cookies) is True

    del cookies["name"]
    assert "name" not in cookies
    assert len(cookies) == 0
    assert dict(cookies) == {}
    assert bool(cookies) is False


def test_cookies_update():
    cookies = httpx.Cookies()
    more_cookies = httpx.Cookies()
    more_cookies.set("name", "value", domain="example.com")

    cookies.update(more_cookies)
    assert dict(cookies) == {"name": "value"}
    assert cookies.get("name", domain="example.com") == "value"


def test_cookies_with_domain():
    cookies = httpx.Cookies()
    cookies.set("name", "value", domain="example.com")
    cookies.set("name", "value", domain="example.org")

    with pytest.raises(httpx.CookieConflict):
        cookies["name"]

    cookies.clear(domain="example.com")
    assert len(cookies) == 1


def test_cookies_with_domain_and_path():
    cookies = httpx.Cookies()
    cookies.set("name", "value", domain="example.com", path="/subpath/1")
    cookies.set("name", "value", domain="example.com", path="/subpath/2")
    cookies.clear(domain="example.com", path="/subpath/1")
    assert len(cookies) == 1
    cookies.delete("name", domain="example.com", path="/subpath/2")
    assert len(cookies) == 0


def test_multiple_set_cookie():
    jar = http.cookiejar.CookieJar()
    headers = [
        (
            b"Set-Cookie",
            b"1P_JAR=2020-08-09-18; expires=Tue, 08-Sep-2099 18:33:35 GMT; "
            b"path=/; domain=.example.org; Secure",
        ),
        (
            b"Set-Cookie",
            b"NID=204=KWdXOuypc86YvRfBSiWoW1dEXfSl_5qI7sxZY4umlk4J35yNTeNEkw15"
            b"MRaujK6uYCwkrtjihTTXZPp285z_xDOUzrdHt4dj0Z5C0VOpbvdLwRdHatHAzQs7"
            b"7TsaiWY78a3qU9r7KP_RbSLvLl2hlhnWFR2Hp5nWKPsAcOhQgSg; expires=Mon, "
            b"08-Feb-2099 18:33:35 GMT; path=/; domain=.example.org; HttpOnly",
        ),
    ]
    request = httpx.Request("GET", "https://www.example.org")
    response = httpx.Response(200, request=request, headers=headers)

    cookies = httpx.Cookies(jar)
    cookies.extract_cookies(response)

    assert len(cookies) == 2


def test_cookies_can_be_a_list_of_tuples():
    cookies_val = [("name1", "val1"), ("name2", "val2")]

    cookies = httpx.Cookies(cookies_val)

    assert len(cookies.items()) == 2
    for k, v in cookies_val:
        assert cookies[k] == v


def test_cookies_repr():
    cookies = httpx.Cookies()
    cookies.set(name="foo", value="bar", domain="http://blah.com")
    cookies.set(name="fizz", value="buzz", domain="http://hello.com")

    assert repr(cookies) == (
        "<Cookies[<Cookie foo=bar for http://blah.com />,"
        " <Cookie fizz=buzz for http://hello.com />]>"
    )
