import pytest

import httpx

# Tests for different host types


def test_url_valid_host():
    url = httpx.URL("https://example.com/")
    assert url.host == "example.com"


def test_url_normalized_host():
    url = httpx.URL("https://EXAMPLE.com/")
    assert url.host == "example.com"


def test_url_ipv4_like_host():
    """rare host names used to quality as IPv4"""
    url = httpx.URL("https://023b76x43144/")
    assert url.host == "023b76x43144"


# Tests for different port types


def test_url_valid_port():
    url = httpx.URL("https://example.com:123/")
    assert url.port == 123


def test_url_normalized_port():
    # If the port matches the scheme default it is normalized to None.
    url = httpx.URL("https://example.com:443/")
    assert url.port is None


def test_url_invalid_port():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://example.com:abc/")
    assert str(exc.value) == "Invalid port: 'abc'"


# Tests for path handling


def test_url_normalized_path():
    url = httpx.URL("https://example.com/abc/def/../ghi/./jkl")
    assert url.path == "/abc/ghi/jkl"


def test_url_escaped_path():
    url = httpx.URL("https://example.com/ /🌟/")
    assert url.raw_path == b"/%20/%F0%9F%8C%9F/"


def test_url_leading_dot_prefix_on_absolute_url():
    url = httpx.URL("https://example.com/../abc")
    assert url.path == "/abc"


def test_url_leading_dot_prefix_on_relative_url():
    url = httpx.URL("../abc")
    assert url.path == "../abc"


# Tests for optional percent encoding


def test_param_requires_encoding():
    url = httpx.URL("http://webservice", params={"u": "with spaces"})
    assert str(url) == "http://webservice?u=with%20spaces"


def test_param_does_not_require_encoding():
    url = httpx.URL("http://webservice", params={"u": "with%20spaces"})
    assert str(url) == "http://webservice?u=with%20spaces"


def test_param_with_existing_escape_requires_encoding():
    url = httpx.URL("http://webservice", params={"u": "http://example.com?q=foo%2Fa"})
    assert str(url) == "http://webservice?u=http%3A%2F%2Fexample.com%3Fq%3Dfoo%252Fa"


# Tests for invalid URLs


def test_url_excessively_long_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com/" + "x" * 100_000)
    assert str(exc.value) == "URL too long"


def test_url_excessively_long_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com", path="/" + "x" * 100_000)
    assert str(exc.value) == "URL component 'path' too long"


def test_url_non_printing_character_in_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com/\n")
    assert str(exc.value) == "Invalid non-printable ASCII character in URL"


def test_url_non_printing_character_in_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com", path="/\n")
    assert (
        str(exc.value)
        == "Invalid non-printable ASCII character in URL component 'path'"
    )


# Test for url components


def test_url_with_components():
    url = httpx.URL(scheme="https", host="www.example.com", path="/")

    assert url.scheme == "https"
    assert url.userinfo == b""
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query == b""
    assert url.fragment == ""

    assert str(url) == "https://www.example.com/"


def test_url_with_invalid_component():
    with pytest.raises(TypeError) as exc:
        httpx.URL(scheme="https", host="www.example.com", incorrect="/")
    assert str(exc.value) == "'incorrect' is an invalid keyword argument for URL()"


def test_url_with_invalid_scheme():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(scheme="~", host="www.example.com", path="/")
    assert str(exc.value) == "Invalid URL component 'scheme'"


def test_url_with_invalid_path():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(scheme="https", host="www.example.com", path="abc")
    assert str(exc.value) == "For absolute URLs, path must be empty or begin with '/'"

    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(path="//abc")
    assert (
        str(exc.value)
        == "URLs with no authority component cannot have a path starting with '//'"
    )

    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(path=":abc")
    assert (
        str(exc.value)
        == "URLs with no scheme component cannot have a path starting with ':'"
    )


def test_url_with_relative_path():
    # This path would be invalid for an absolute URL, but is valid as a relative URL.
    url = httpx.URL(path="abc")
    assert url.path == "abc"


# Tests for percent encoding across path, query, and fragment...


def test_path_percent_encoding():
    # Test percent encoding for SUB_DELIMS ALPHA NUM and allowable GEN_DELIMS
    url = httpx.URL("https://example.com/!$&'()*+,;= abc ABC 123 :/[]@")
    assert url.raw_path == b"/!$&'()*+,;=%20abc%20ABC%20123%20:/[]@"
    assert url.path == "/!$&'()*+,;= abc ABC 123 :/[]@"
    assert url.query == b""
    assert url.fragment == ""


def test_query_percent_encoding():
    # Test percent encoding for SUB_DELIMS ALPHA NUM and allowable GEN_DELIMS
    url = httpx.URL("https://example.com/?!$&'()*+,;= abc ABC 123 :/[]@" + "?")
    assert url.raw_path == b"/?!$&'()*+,;=%20abc%20ABC%20123%20:%2F[]@?"
    assert url.path == "/"
    assert url.query == b"!$&'()*+,;=%20abc%20ABC%20123%20:%2F[]@?"
    assert url.fragment == ""


def test_fragment_percent_encoding():
    # Test percent encoding for SUB_DELIMS ALPHA NUM and allowable GEN_DELIMS
    url = httpx.URL("https://example.com/#!$&'()*+,;= abc ABC 123 :/[]@" + "?#")
    assert url.raw_path == b"/"
    assert url.path == "/"
    assert url.query == b""
    assert url.fragment == "!$&'()*+,;= abc ABC 123 :/[]@?#"
