import pytest

import httpx


def test_headers():
    h = httpx.Headers([("a", "123"), ("a", "456"), ("b", "789")])
    assert "a" in h
    assert "A" in h
    assert "b" in h
    assert "B" in h
    assert "c" not in h
    assert h["a"] == "123, 456"
    assert h.get("a") == "123, 456"
    assert h.get("nope", default=None) is None
    assert h.get_list("a") == ["123", "456"]

    assert list(h.keys()) == ["a", "b"]
    assert list(h.values()) == ["123, 456", "789"]
    assert list(h.items()) == [("a", "123, 456"), ("b", "789")]
    assert h.multi_items() == [("a", "123"), ("a", "456"), ("b", "789")]
    assert list(h) == ["a", "b"]
    assert dict(h) == {"a": "123, 456", "b": "789"}
    assert repr(h) == "Headers([('a', '123'), ('a', '456'), ('b', '789')])"
    assert h == [("a", "123"), ("b", "789"), ("a", "456")]
    assert h == [("a", "123"), ("A", "456"), ("b", "789")]
    assert h == {"a": "123", "A": "456", "b": "789"}
    assert h != "a: 123\nA: 456\nb: 789"

    h = httpx.Headers({"a": "123", "b": "789"})
    assert h["A"] == "123"
    assert h["B"] == "789"
    assert h.raw == [(b"a", b"123"), (b"b", b"789")]
    assert repr(h) == "Headers({'a': '123', 'b': '789'})"


def test_header_mutations():
    h = httpx.Headers()
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


def test_copy_headers_method():
    headers = httpx.Headers({"custom": "example"})
    headers_copy = headers.copy()
    assert headers == headers_copy
    assert headers is not headers_copy


def test_copy_headers_init():
    headers = httpx.Headers({"custom": "example"})
    headers_copy = httpx.Headers(headers)
    assert headers == headers_copy


def test_headers_insert_retains_ordering():
    headers = httpx.Headers({"a": "a", "b": "b", "c": "c"})
    headers["b"] = "123"
    assert list(headers.values()) == ["a", "123", "c"]


def test_headers_insert_appends_if_new():
    headers = httpx.Headers({"a": "a", "b": "b", "c": "c"})
    headers["d"] = "123"
    assert list(headers.values()) == ["a", "b", "c", "123"]


def test_headers_insert_removes_all_existing():
    headers = httpx.Headers([("a", "123"), ("a", "456")])
    headers["a"] = "789"
    assert dict(headers) == {"a": "789"}


def test_headers_delete_removes_all_existing():
    headers = httpx.Headers([("a", "123"), ("a", "456")])
    del headers["a"]
    assert dict(headers) == {}


def test_headers_dict_repr():
    """
    Headers should display with a dict repr by default.
    """
    headers = httpx.Headers({"custom": "example"})
    assert repr(headers) == "Headers({'custom': 'example'})"


def test_headers_encoding_in_repr():
    """
    Headers should display an encoding in the repr if required.
    """
    headers = httpx.Headers({b"custom": "example ☃".encode("utf-8")})
    assert repr(headers) == "Headers({'custom': 'example ☃'}, encoding='utf-8')"


def test_headers_list_repr():
    """
    Headers should display with a list repr if they include multiple identical keys.
    """
    headers = httpx.Headers([("custom", "example 1"), ("custom", "example 2")])
    assert (
        repr(headers) == "Headers([('custom', 'example 1'), ('custom', 'example 2')])"
    )


def test_headers_decode_ascii():
    """
    Headers should decode as ascii by default.
    """
    raw_headers = [(b"Custom", b"Example")]
    headers = httpx.Headers(raw_headers)
    assert dict(headers) == {"custom": "Example"}
    assert headers.encoding == "ascii"


def test_headers_decode_utf_8():
    """
    Headers containing non-ascii codepoints should default to decoding as utf-8.
    """
    raw_headers = [(b"Custom", "Code point: ☃".encode("utf-8"))]
    headers = httpx.Headers(raw_headers)
    assert dict(headers) == {"custom": "Code point: ☃"}
    assert headers.encoding == "utf-8"


def test_headers_decode_iso_8859_1():
    """
    Headers containing non-UTF-8 codepoints should default to decoding as iso-8859-1.
    """
    raw_headers = [(b"Custom", "Code point: ÿ".encode("iso-8859-1"))]
    headers = httpx.Headers(raw_headers)
    assert dict(headers) == {"custom": "Code point: ÿ"}
    assert headers.encoding == "iso-8859-1"


def test_headers_decode_explicit_encoding():
    """
    An explicit encoding may be set on headers in order to force a
    particular decoding.
    """
    raw_headers = [(b"Custom", "Code point: ☃".encode("utf-8"))]
    headers = httpx.Headers(raw_headers)
    headers.encoding = "iso-8859-1"
    assert dict(headers) == {"custom": "Code point: â\x98\x83"}
    assert headers.encoding == "iso-8859-1"


def test_multiple_headers():
    """
    `Headers.get_list` should support both split_commas=False and split_commas=True.
    """
    h = httpx.Headers([("set-cookie", "a, b"), ("set-cookie", "c")])
    assert h.get_list("Set-Cookie") == ["a, b", "c"]

    h = httpx.Headers([("vary", "a, b"), ("vary", "c")])
    assert h.get_list("Vary", split_commas=True) == ["a", "b", "c"]


@pytest.mark.parametrize("header", ["authorization", "proxy-authorization"])
def test_sensitive_headers(header):
    """
    Some headers should be obfuscated because they contain sensitive data.
    """
    value = "s3kr3t"
    h = httpx.Headers({header: value})
    assert repr(h) == "Headers({'%s': '[secure]'})" % header


@pytest.mark.parametrize(
    "headers, output",
    [
        ([("content-type", "text/html")], [("content-type", "text/html")]),
        ([("authorization", "s3kr3t")], [("authorization", "[secure]")]),
        ([("proxy-authorization", "s3kr3t")], [("proxy-authorization", "[secure]")]),
    ],
)
def test_obfuscate_sensitive_headers(headers, output):
    as_dict = {k: v for k, v in output}
    headers_class = httpx.Headers({k: v for k, v in headers})
    assert repr(headers_class) == f"Headers({as_dict!r})"


@pytest.mark.parametrize(
    "value, expected",
    (
        (
            '<http:/.../front.jpeg>; rel=front; type="image/jpeg"',
            [{"url": "http:/.../front.jpeg", "rel": "front", "type": "image/jpeg"}],
        ),
        ("<http:/.../front.jpeg>", [{"url": "http:/.../front.jpeg"}]),
        ("<http:/.../front.jpeg>;", [{"url": "http:/.../front.jpeg"}]),
        (
            '<http:/.../front.jpeg>; type="image/jpeg",<http://.../back.jpeg>;',
            [
                {"url": "http:/.../front.jpeg", "type": "image/jpeg"},
                {"url": "http://.../back.jpeg"},
            ],
        ),
        ("", []),
    ),
)
def test_parse_header_links(value, expected):
    all_links = httpx.Response(200, headers={"link": value}).links.values()
    assert all(link in all_links for link in expected)


def test_parse_header_links_no_link():
    all_links = httpx.Response(200).links
    assert all_links == {}
