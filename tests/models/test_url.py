import pytest

from httpx import URL
from httpx.exceptions import InvalidURL


def test_idna_url():
    url = URL("http://中国.icom.museum:80/")
    assert url == URL("http://xn--fiqs8s.icom.museum:80/")
    assert url.host == "xn--fiqs8s.icom.museum"
    assert url.port == 80

    url = URL("https://faß.de")
    assert url == URL("https://xn--fa-hia.de") # IDNA 2008
    assert url.host == "xn--fa-hia.de"
    assert url.port == 443

    url = URL("https://βόλος.com:443")
    assert url == URL("https://xn--nxasmm1c.com:443") # IDNA 2008
    assert url.host == "xn--nxasmm1c.com"
    assert url.port == 443

    url = URL("http://ශ්‍රී.com:444")
    assert url == URL("http://xn--10cl1a0b660p.com:444") # IDNA 2008
    assert url.host == "xn--10cl1a0b660p.com"
    assert url.scheme == "http"
    assert url.port == 444

    url = URL("https://نامه‌ای.com:4433")
    assert url == URL("https://xn--mgba3gch31f060k.com:4433") # IDNA 2008
    assert url.host == "xn--mgba3gch31f060k.com"
    assert url.scheme == "https"
    assert url.port == 4433


def test_url():
    url = URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url.scheme == "https"
    assert url.host == "example.org"
    assert url.port == 123
    assert url.authority == "example.org:123"
    assert url.path == "/path/to/somewhere"
    assert url.query == "abc=123"
    assert url.fragment == "anchor"
    assert (
        repr(url) == "URL('https://example.org:123/path/to/somewhere?abc=123#anchor')"
    )

    new = url.copy_with(scheme="http")
    assert new == URL("http://example.org:123/path/to/somewhere?abc=123#anchor")
    assert new.scheme == "http"


def test_url_eq_str():
    url = URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url == "https://example.org:123/path/to/somewhere?abc=123#anchor"
    assert str(url) == url


def test_url_params():
    url = URL("https://example.org:123/path/to/somewhere", params={"a": "123"})
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"

    url = URL("https://example.org:123/path/to/somewhere?b=456", params={"a": "123"})
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"


def test_url_join():
    """
    Some basic URL joining tests.
    """
    url = URL("https://example.org:123/path/to/somewhere")
    assert url.join("/somewhere-else") == "https://example.org:123/somewhere-else"
    assert (
        url.join("somewhere-else") == "https://example.org:123/path/to/somewhere-else"
    )
    assert (
        url.join("../somewhere-else") == "https://example.org:123/path/somewhere-else"
    )
    assert url.join("../../somewhere-else") == "https://example.org:123/somewhere-else"


def test_url_join_rfc3986():
    """
    URL joining tests, as-per reference examples in RFC 3986.

    https://tools.ietf.org/html/rfc3986#section-5.4
    """

    url = URL("http://example.com/b/c/d;p?q")

    with pytest.raises(InvalidURL):
        assert url.join("g:h") == "g:h"

    assert url.join("g") == "http://example.com/b/c/g"
    assert url.join("./g") == "http://example.com/b/c/g"
    assert url.join("g/") == "http://example.com/b/c/g/"
    assert url.join("/g") == "http://example.com/g"
    assert url.join("//g") == "http://g"
    assert url.join("?y") == "http://example.com/b/c/d;p?y"
    assert url.join("g?y") == "http://example.com/b/c/g?y"
    assert url.join("#s") == "http://example.com/b/c/d;p?q#s"
    assert url.join("g#s") == "http://example.com/b/c/g#s"
    assert url.join("g?y#s") == "http://example.com/b/c/g?y#s"
    assert url.join(";x") == "http://example.com/b/c/;x"
    assert url.join("g;x") == "http://example.com/b/c/g;x"
    assert url.join("g;x?y#s") == "http://example.com/b/c/g;x?y#s"
    assert url.join("") == "http://example.com/b/c/d;p?q"
    assert url.join(".") == "http://example.com/b/c/"
    assert url.join("./") == "http://example.com/b/c/"
    assert url.join("..") == "http://example.com/b/"
    assert url.join("../") == "http://example.com/b/"
    assert url.join("../g") == "http://example.com/b/g"
    assert url.join("../..") == "http://example.com/"
    assert url.join("../../") == "http://example.com/"
    assert url.join("../../g") == "http://example.com/g"

    assert url.join("../../../g") == "http://example.com/g"
    assert url.join("../../../../g") == "http://example.com/g"

    assert url.join("/./g") == "http://example.com/g"
    assert url.join("/../g") == "http://example.com/g"
    assert url.join("g.") == "http://example.com/b/c/g."
    assert url.join(".g") == "http://example.com/b/c/.g"
    assert url.join("g..") == "http://example.com/b/c/g.."
    assert url.join("..g") == "http://example.com/b/c/..g"

    assert url.join("./../g") == "http://example.com/b/g"
    assert url.join("./g/.") == "http://example.com/b/c/g/"
    assert url.join("g/./h") == "http://example.com/b/c/g/h"
    assert url.join("g/../h") == "http://example.com/b/c/h"
    assert url.join("g;x=1/./y") == "http://example.com/b/c/g;x=1/y"
    assert url.join("g;x=1/../y") == "http://example.com/b/c/y"

    assert url.join("g?y/./x") == "http://example.com/b/c/g?y/./x"
    assert url.join("g?y/../x") == "http://example.com/b/c/g?y/../x"
    assert url.join("g#s/./x") == "http://example.com/b/c/g#s/./x"
    assert url.join("g#s/../x") == "http://example.com/b/c/g#s/../x"


def test_url_set():
    urls = (
        URL("http://example.org:123/path/to/somewhere"),
        URL("http://example.org:123/path/to/somewhere/else"),
    )

    url_set = set(urls)

    assert all(url in urls for url in url_set)


def test_hsts_preload_converted_to_https():
    url = URL("http://www.paypal.com")

    assert url.is_ssl
    assert url.scheme == "https"
    assert url == "https://www.paypal.com"
