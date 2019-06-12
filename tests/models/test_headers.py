import http3


def test_headers():
    h = http3.Headers([("a", "123"), ("a", "456"), ("b", "789")])
    assert "a" in h
    assert "A" in h
    assert "b" in h
    assert "B" in h
    assert "c" not in h
    assert h["a"] == "123, 456"
    assert h.get("a") == "123, 456"
    assert h.get("nope", default=None) is None
    assert h.getlist("a") == ["123", "456"]
    assert h.keys() == ["a", "a", "b"]
    assert h.values() == ["123", "456", "789"]
    assert h.items() == [("a", "123"), ("a", "456"), ("b", "789")]
    assert list(h) == ["a", "a", "b"]
    assert dict(h) == {"a": "123, 456", "b": "789"}
    assert repr(h) == "Headers([('a', '123'), ('a', '456'), ('b', '789')])"
    assert h == http3.Headers([("a", "123"), ("b", "789"), ("a", "456")])
    assert h != [("a", "123"), ("A", "456"), ("b", "789")]

    h = http3.Headers({"a": "123", "b": "789"})
    assert h["A"] == "123"
    assert h["B"] == "789"
    assert h.raw == [(b"a", b"123"), (b"b", b"789")]
    assert repr(h) == "Headers({'a': '123', 'b': '789'})"


def test_header_mutations():
    h = http3.Headers()
    assert dict(h) == {}
    h["a"] = "1"
    assert dict(h) == {"a": "1"}
    h["a"] = "2"
    assert dict(h) == {"a": "2"}
    h.setdefault("a", "3")
    assert dict(h) == {"a": "2"}
    h.setdefault("b", "4")
    assert dict(h) == {"a": "2", "b": "4"}
    del h["a"]
    assert dict(h) == {"b": "4"}
    assert h.raw == [(b"b", b"4")]


def test_copy_headers():
    headers = http3.Headers({"custom": "example"})
    headers_copy = http3.Headers(headers)
    assert headers == headers_copy


def test_headers_insert_retains_ordering():
    headers = http3.Headers({"a": "a", "b": "b", "c": "c"})
    headers["b"] = "123"
    assert list(headers.values()) == ["a", "123", "c"]


def test_headers_insert_appends_if_new():
    headers = http3.Headers({"a": "a", "b": "b", "c": "c"})
    headers["d"] = "123"
    assert list(headers.values()) == ["a", "b", "c", "123"]


def test_headers_insert_removes_all_existing():
    headers = http3.Headers([("a", "123"), ("a", "456")])
    headers["a"] = "789"
    assert dict(headers) == {"a": "789"}


def test_headers_delete_removes_all_existing():
    headers = http3.Headers([("a", "123"), ("a", "456")])
    del headers["a"]
    assert dict(headers) == {}


def test_headers_dict_repr():
    """
    Headers should display with a dict repr by default.
    """
    headers = http3.Headers({"custom": "example"})
    assert repr(headers) == "Headers({'custom': 'example'})"


def test_headers_encoding_in_repr():
    """
    Headers should display an encoding in the repr if required.
    """
    headers = http3.Headers({b"custom": "example ☃".encode("utf-8")})
    assert repr(headers) == "Headers({'custom': 'example ☃'}, encoding='utf-8')"


def test_headers_list_repr():
    """
    Headers should display with a list repr if they include multiple identical keys.
    """
    headers = http3.Headers([("custom", "example 1"), ("custom", "example 2")])
    assert (
        repr(headers) == "Headers([('custom', 'example 1'), ('custom', 'example 2')])"
    )


def test_headers_decode_ascii():
    """
    Headers should decode as ascii by default.
    """
    raw_headers = [(b"Custom", b"Example")]
    headers = http3.Headers(raw_headers)
    assert dict(headers) == {"custom": "Example"}
    assert headers.encoding == "ascii"


def test_headers_decode_utf_8():
    """
    Headers containing non-ascii codepoints should default to decoding as utf-8.
    """
    raw_headers = [(b"Custom", "Code point: ☃".encode("utf-8"))]
    headers = http3.Headers(raw_headers)
    assert dict(headers) == {"custom": "Code point: ☃"}
    assert headers.encoding == "utf-8"


def test_headers_decode_iso_8859_1():
    """
    Headers containing non-UTF-8 codepoints should default to decoding as iso-8859-1.
    """
    raw_headers = [(b"Custom", "Code point: ÿ".encode("iso-8859-1"))]
    headers = http3.Headers(raw_headers)
    assert dict(headers) == {"custom": "Code point: ÿ"}
    assert headers.encoding == "iso-8859-1"


def test_headers_decode_explicit_encoding():
    """
    An explicit encoding may be set on headers in order to force a
    particular decoding.
    """
    raw_headers = [(b"Custom", "Code point: ☃".encode("utf-8"))]
    headers = http3.Headers(raw_headers)
    headers.encoding = "iso-8859-1"
    assert dict(headers) == {"custom": "Code point: â\x98\x83"}
    assert headers.encoding == "iso-8859-1"


def test_multiple_headers():
    """
    Most headers should split by commas for `getlist`, except 'Set-Cookie'.
    """
    h = http3.Headers([("set-cookie", "a, b"), ("set-cookie", "c")])
    h.getlist("Set-Cookie") == ["a, b", "b"]

    h = http3.Headers([("vary", "a, b"), ("vary", "c")])
    h.getlist("Vary") == ["a", "b", "c"]
