import pytest

import httpx
from httpx._urlparse import urlparse


def test_urlparse():
    url = urlparse("https://www.example.com/")

    assert url.scheme == "https"
    assert url.userinfo == ""
    assert url.netloc == "www.example.com"
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query is None
    assert url.fragment is None

    assert str(url) == "https://www.example.com/"


def test_urlparse_no_scheme():
    url = urlparse("://example.com")
    assert url.scheme == ""
    assert url.host == "example.com"
    assert url.path == ""


def test_urlparse_no_authority():
    url = urlparse("http://")
    assert url.scheme == "http"
    assert url.host == ""
    assert url.path == ""


# Tests for different host types


def test_urlparse_valid_host():
    url = urlparse("https://example.com/")
    assert url.host == "example.com"


def test_urlparse_normalized_host():
    url = urlparse("https://EXAMPLE.com/")
    assert url.host == "example.com"


def test_urlparse_valid_ipv4():
    url = urlparse("https://1.2.3.4/")
    assert url.host == "1.2.3.4"


def test_urlparse_invalid_ipv4():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://999.999.999.999/")
    assert str(exc.value) == "Invalid IPv4 address"


def test_urlparse_valid_ipv6():
    url = urlparse("https://[2001:db8::ff00:42:8329]/")
    assert url.host == "2001:db8::ff00:42:8329"


def test_urlparse_invalid_ipv6():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://[2001]/")
    assert str(exc.value) == "Invalid IPv6 address"


def test_urlparse_unescaped_idna_host():
    url = urlparse("https://中国.icom.museum/")
    assert url.host == "xn--fiqs8s.icom.museum"


def test_urlparse_escaped_idna_host():
    url = urlparse("https://xn--fiqs8s.icom.museum/")
    assert url.host == "xn--fiqs8s.icom.museum"


def test_urlparse_invalid_idna_host():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://☃.com/")
    assert str(exc.value) == "Invalid IDNA hostname"


# Tests for different port types


def test_urlparse_valid_port():
    url = urlparse("https://example.com:123/")
    assert url.port == 123


def test_urlparse_normalized_port():
    # If the port matches the scheme default it is normalized to None.
    url = urlparse("https://example.com:443/")
    assert url.port is None


def test_urlparse_invalid_port():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://example.com:abc/")
    assert str(exc.value) == "Invalid port"


# Tests for path handling


def test_urlparse_normalized_path():
    url = urlparse("https://example.com/abc/def/../ghi/./jkl")
    assert url.path == "/abc/ghi/jkl"


def test_urlparse_escaped_path():
    url = urlparse("https://example.com/ /🌟/")
    assert url.path == "/%20/%F0%9F%8C%9F/"


def test_urlparse_leading_dot_prefix_on_absolute_url():
    url = urlparse("https://example.com/../abc")
    assert url.path == "/abc"


def test_urlparse_leading_dot_prefix_on_relative_url():
    url = urlparse("../abc")
    assert url.path == "../abc"


# Tests for invalid URLs


def test_urlparse_excessively_long_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://www.example.com/" + "x" * 100_000)
    assert str(exc.value) == "URL too long"


def test_urlparse_excessively_long_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://www.example.com", path="/" + "x" * 100_000)
    assert str(exc.value) == "URL component 'path' too long"


def test_urlparse_non_printing_character_in_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://www.example.com/\n")
    assert str(exc.value) == "Invalid non-printable ASCII character in URL"


def test_urlparse_non_printing_character_in_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse("https://www.example.com", path="/\n")
    assert (
        str(exc.value)
        == "Invalid non-printable ASCII character in URL component 'path'"
    )


# Test for urlparse components


def test_urlparse_with_components():
    url = urlparse(scheme="https", host="www.example.com", path="/")

    assert url.scheme == "https"
    assert url.userinfo == ""
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query is None
    assert url.fragment is None

    assert str(url) == "https://www.example.com/"


def test_urlparse_with_invalid_component():
    with pytest.raises(TypeError) as exc:
        urlparse(scheme="https", host="www.example.com", incorrect="/")
    assert str(exc.value) == "'incorrect' is an invalid keyword argument for urlparse()"


def test_urlparse_with_invalid_scheme():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse(scheme="~", host="www.example.com", path="/")
    assert str(exc.value) == "Invalid URL component 'scheme'"


def test_urlparse_with_invalid_path():
    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse(scheme="https", host="www.example.com", path="abc")
    assert str(exc.value) == "For absolute URLs, path must be empty or begin with '/'"

    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse(path="//abc")
    assert (
        str(exc.value)
        == "URLs with no authority component cannot have a path starting with '//'"
    )

    with pytest.raises(httpx.InvalidURL) as exc:
        urlparse(path=":abc")
    assert (
        str(exc.value)
        == "URLs with no scheme component cannot have a path starting with ':'"
    )


def test_urlparse_with_relative_path():
    # This path would be invalid for an absolute URL, but is valid as a relative URL.
    url = urlparse(path="abc")
    assert url.path == "abc"


# Tests for accessing and modifying `urlparse` results.


def test_copy_with():
    url = urlparse("https://www.example.com/")
    assert str(url) == "https://www.example.com/"

    url = url.copy_with()
    assert str(url) == "https://www.example.com/"

    url = url.copy_with(scheme="http")
    assert str(url) == "http://www.example.com/"

    url = url.copy_with(netloc="example.com")
    assert str(url) == "http://example.com/"

    url = url.copy_with(path="/abc")
    assert str(url) == "http://example.com/abc"
