import pytest

import httpx


def test_urlparse():
    url = httpx.URL("https://www.example.com/")

    assert url.scheme == "https"
    assert url.userinfo == b""
    assert url.netloc == b"www.example.com"
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query == b""
    assert url.fragment == ""

    assert str(url) == "https://www.example.com/"


def test_urlparse_no_scheme():
    url = httpx.URL("://example.com")
    assert url.scheme == ""
    assert url.host == "example.com"
    assert url.path == "/"


def test_urlparse_no_authority():
    url = httpx.URL("http://")
    assert url.scheme == "http"
    assert url.host == ""
    assert url.path == "/"


# Tests for different host types


def test_urlparse_valid_host():
    url = httpx.URL("https://example.com/")
    assert url.host == "example.com"


def test_urlparse_normalized_host():
    url = httpx.URL("https://EXAMPLE.com/")
    assert url.host == "example.com"


def test_urlparse_ipv4_like_host():
    """rare host names used to quality as IPv4"""
    url = httpx.URL("https://023b76x43144/")
    assert url.host == "023b76x43144"


def test_urlparse_valid_ipv4():
    url = httpx.URL("https://1.2.3.4/")
    assert url.host == "1.2.3.4"


def test_urlparse_invalid_ipv4():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://999.999.999.999/")
    assert str(exc.value) == "Invalid IPv4 address: '999.999.999.999'"


def test_urlparse_valid_ipv6():
    url = httpx.URL("https://[2001:db8::ff00:42:8329]/")
    assert url.host == "2001:db8::ff00:42:8329"


def test_urlparse_invalid_ipv6():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://[2001]/")
    assert str(exc.value) == "Invalid IPv6 address: '[2001]'"


def test_urlparse_unescaped_idna_host():
    url = httpx.URL("https://中国.icom.museum/")
    assert url.raw_host == b"xn--fiqs8s.icom.museum"


def test_urlparse_escaped_idna_host():
    url = httpx.URL("https://xn--fiqs8s.icom.museum/")
    assert url.raw_host == b"xn--fiqs8s.icom.museum"


def test_urlparse_invalid_idna_host():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://☃.com/")
    assert str(exc.value) == "Invalid IDNA hostname: '☃.com'"


# Tests for different port types


def test_urlparse_valid_port():
    url = httpx.URL("https://example.com:123/")
    assert url.port == 123


def test_urlparse_normalized_port():
    # If the port matches the scheme default it is normalized to None.
    url = httpx.URL("https://example.com:443/")
    assert url.port is None


def test_urlparse_invalid_port():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://example.com:abc/")
    assert str(exc.value) == "Invalid port: 'abc'"


# Tests for path handling


def test_urlparse_normalized_path():
    url = httpx.URL("https://example.com/abc/def/../ghi/./jkl")
    assert url.path == "/abc/ghi/jkl"


def test_urlparse_escaped_path():
    url = httpx.URL("https://example.com/ /🌟/")
    assert url.raw_path == b"/%20/%F0%9F%8C%9F/"


def test_urlparse_leading_dot_prefix_on_absolute_url():
    url = httpx.URL("https://example.com/../abc")
    assert url.path == "/abc"


def test_urlparse_leading_dot_prefix_on_relative_url():
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


def test_urlparse_excessively_long_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com/" + "x" * 100_000)
    assert str(exc.value) == "URL too long"


def test_urlparse_excessively_long_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com", path="/" + "x" * 100_000)
    assert str(exc.value) == "URL component 'path' too long"


def test_urlparse_non_printing_character_in_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com/\n")
    assert str(exc.value) == "Invalid non-printable ASCII character in URL"


def test_urlparse_non_printing_character_in_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com", path="/\n")
    assert (
        str(exc.value)
        == "Invalid non-printable ASCII character in URL component 'path'"
    )


# Test for urlparse components


def test_urlparse_with_components():
    url = httpx.URL(scheme="https", host="www.example.com", path="/")

    assert url.scheme == "https"
    assert url.userinfo == b""
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query == b""
    assert url.fragment == ""

    assert str(url) == "https://www.example.com/"


def test_urlparse_with_invalid_component():
    with pytest.raises(TypeError) as exc:
        httpx.URL(scheme="https", host="www.example.com", incorrect="/")
    assert str(exc.value) == "'incorrect' is an invalid keyword argument for URL()"


def test_urlparse_with_invalid_scheme():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(scheme="~", host="www.example.com", path="/")
    assert str(exc.value) == "Invalid URL component 'scheme'"


def test_urlparse_with_invalid_path():
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


def test_urlparse_with_relative_path():
    # This path would be invalid for an absolute URL, but is valid as a relative URL.
    url = httpx.URL(path="abc")
    assert url.path == "abc"


# Tests for accessing and modifying `urlparse` results.


def test_copy_with():
    url = httpx.URL("https://www.example.com/")
    assert str(url) == "https://www.example.com/"

    url = url.copy_with()
    assert str(url) == "https://www.example.com/"

    url = url.copy_with(scheme="http")
    assert str(url) == "http://www.example.com/"

    url = url.copy_with(netloc=b"example.com")
    assert str(url) == "http://example.com/"

    url = url.copy_with(path="/abc")
    assert str(url) == "http://example.com/abc"


# Tests for percent encoding across path, query, and fragement...


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
