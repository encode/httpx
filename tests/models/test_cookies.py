import pytest
from http3 import CookieConflict, Cookies


def test_cookies():
    cookies = Cookies({"name": "value"})
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
    cookies = Cookies()
    more_cookies = Cookies()
    more_cookies.set("name", "value", domain="example.com")

    cookies.update(more_cookies)
    assert dict(cookies) == {"name": "value"}
    assert cookies.get("name", domain="example.com") == "value"


def test_cookies_with_domain():
    cookies = Cookies()
    cookies.set("name", "value", domain="example.com")
    cookies.set("name", "value", domain="example.org")

    with pytest.raises(CookieConflict):
        cookies["name"]

    cookies.clear(domain="example.com")
    assert len(cookies) == 1


def test_cookies_with_domain_and_path():
    cookies = Cookies()
    cookies.set("name", "value", domain="example.com", path="/subpath/1")
    cookies.set("name", "value", domain="example.com", path="/subpath/2")
    cookies.clear(domain="example.com", path="/subpath/1")
    assert len(cookies) == 1
    cookies.delete("name", domain="example.com", path="/subpath/2")
    assert len(cookies) == 0
