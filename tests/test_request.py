import httpx
import pytest


class ByteIterator:
    def __init__(self, buffer=b""):
        self._buffer = buffer
    
    def next(self) -> bytes:
        buffer = self._buffer
        self._buffer = b''
        return buffer


def test_request():
    r = httpx.Request("GET", "https://example.com")

    assert repr(r) == "<Request [GET 'https://example.com']>"
    assert r.method == "GET"
    assert r.url == "https://example.com"
    assert r.headers == {
        "Host": "example.com"
    }
    assert r.read() == b""

def test_request_bytes():
    content = b"Hello, world"
    r = httpx.Request("POST", "https://example.com", content=content)

    assert repr(r) == "<Request [POST 'https://example.com']>"
    assert r.method == "POST"
    assert r.url == "https://example.com"
    assert r.headers == {
        "Host": "example.com",
        "Content-Length": "12",
    }
    assert r.read() == b"Hello, world"


def test_request_stream():
    i = ByteIterator(b"Hello, world")
    stream = httpx.HTTPStream(i.next, None)
    r = httpx.Request("POST", "https://example.com", content=stream)

    assert repr(r) == "<Request [POST 'https://example.com']>"
    assert r.method == "POST"
    assert r.url == "https://example.com"
    assert r.headers == {
        "Host": "example.com",
        "Transfer-Encoding": "chunked",
    }
    assert r.read() == b"Hello, world"


def test_request_json():
    data = httpx.JSON({"msg": "Hello, world"})
    r = httpx.Request("POST", "https://example.com", content=data)

    assert repr(r) == "<Request [POST 'https://example.com']>"
    assert r.method == "POST"
    assert r.url == "https://example.com"
    assert r.headers == {
        "Host": "example.com",
        "Content-Length": "22",
        "Content-Type": "application/json",
    }
    assert r.read() == b'{"msg":"Hello, world"}'


def test_request_empty_post():
    r = httpx.Request("POST", "https://example.com")

    assert repr(r) == "<Request [POST 'https://example.com']>"
    assert r.method == "POST"
    assert r.url == "https://example.com"
    assert r.headers == {
        "Host": "example.com",
        "Content-Length": "0",
    }
    assert r.read() == b''


def test_request_invalid_scheme():
    with pytest.raises(ValueError):
        httpx.Request("GET", "ws://example.com")


def test_request_missing_host():
    with pytest.raises(ValueError):
        r = httpx.Request("GET", "https:/example.com")
