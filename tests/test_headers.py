import httpx
import pytest


def test_headers_from_dict():
    headers = httpx.Headers({
        'Content-Length': '1024',
        'Content-Type': 'text/plain; charset=utf-8',
    })
    assert headers['Content-Length'] == '1024'
    assert headers['Content-Type'] == 'text/plain; charset=utf-8'


def test_headers_from_list():
    headers = httpx.Headers([
        ('Location', 'https://www.example.com'),
        ('Set-Cookie', 'session_id=3498jj489jhb98jn'),
    ])
    assert headers['Location'] == 'https://www.example.com'
    assert headers['Set-Cookie'] == 'session_id=3498jj489jhb98jn'


def test_header_keys():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert list(h.keys()) == ["Accept", "User-Agent"]


def test_header_values():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert list(h.values()) == ["*/*", "python/httpx"]


def test_header_items():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert list(h.items()) == [("Accept", "*/*"), ("User-Agent", "python/httpx")]


def test_header_get():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert h.get("User-Agent") == "python/httpx"
    assert h.get("user-agent") == "python/httpx"
    assert h.get("missing") is None


def test_header_copy_set():
    h = httpx.Headers({"Expires": "0"})
    h = h.copy_set("Expires", "Wed, 21 Oct 2015 07:28:00 GMT")
    assert h == httpx.Headers({"Expires": "Wed, 21 Oct 2015 07:28:00 GMT"})

    h = httpx.Headers({"Expires": "0"})
    h = h.copy_set("expires", "Wed, 21 Oct 2015 07:28:00 GMT")
    assert h == httpx.Headers({"Expires": "Wed, 21 Oct 2015 07:28:00 GMT"})


def test_header_copy_remove():
    h = httpx.Headers({"Accept": "*/*"})
    h = h.copy_remove("Accept")
    assert h == httpx.Headers({})

    h = httpx.Headers({"Accept": "*/*"})
    h = h.copy_remove("accept")
    assert h == httpx.Headers({})


def test_header_getitem():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert h["User-Agent"] == "python/httpx"
    assert h["user-agent"] == "python/httpx"
    with pytest.raises(KeyError):
        h["missing"]


def test_header_contains():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert "User-Agent" in h
    assert "user-agent" in h
    assert "missing" not in h


def test_header_bool():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert bool(h)
    h = httpx.Headers()
    assert not bool(h)


def test_header_iter():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert [k for k in h] == ["Accept", "User-Agent"]


def test_header_len():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert len(h) == 2


def test_header_repr():
    h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
    assert repr(h) == "<Headers {'Accept': '*/*', 'User-Agent': 'python/httpx'}>"


def test_header_invalid_name():
    with pytest.raises(ValueError):
        httpx.Headers({"Accept\n": "*/*"})


def test_header_invalid_value():
    with pytest.raises(ValueError):
        httpx.Headers({"Accept": "*/*\n"})
