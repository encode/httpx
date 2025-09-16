import httpx


class ByteIterator:
    def __init__(self, buffer=b""):
        self._buffer = buffer
    
    def next(self) -> bytes:
        buffer = self._buffer
        self._buffer = b''
        return buffer


def test_response():
    r = httpx.Response(200)

    assert repr(r) == "<Response [200 OK]>"
    assert r.status_code == 200
    assert r.headers == {'Content-Length': '0'}
    assert r.read() == b""


def test_response_204():
    r = httpx.Response(204)

    assert repr(r) == "<Response [204 No Content]>"
    assert r.status_code == 204
    assert r.headers == {}
    assert r.read() == b""


def test_response_bytes():
    content = b"Hello, world"
    r = httpx.Response(200, content=content)

    assert repr(r) == "<Response [200 OK]>"
    assert r.headers == {
        "Content-Length": "12",
    }
    assert r.read() == b"Hello, world"


def test_response_stream():
    i = ByteIterator(b"Hello, world")
    stream = httpx.HTTPStream(i.next, None)
    r = httpx.Response(200, content=stream)

    assert repr(r) == "<Response [200 OK]>"
    assert r.headers == {
        "Transfer-Encoding": "chunked",
    }
    assert r.read() == b"Hello, world"


def test_response_json():
    data = httpx.JSON({"msg": "Hello, world"})
    r = httpx.Response(200, content=data)

    assert repr(r) == "<Response [200 OK]>"
    assert r.headers == {
        "Content-Length": "22",
        "Content-Type": "application/json",
    }
    assert r.read() == b'{"msg":"Hello, world"}'
