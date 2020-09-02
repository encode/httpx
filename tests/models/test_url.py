import pytest

import httpx


@pytest.mark.parametrize(
    "given,idna,host,scheme,port",
    [
        (
            "http://中国.icom.museum:80/",
            "http://xn--fiqs8s.icom.museum:80/",
            "xn--fiqs8s.icom.museum",
            "http",
            80,
        ),
        (
            "http://Königsgäßchen.de",
            "http://xn--knigsgchen-b4a3dun.de",
            "xn--knigsgchen-b4a3dun.de",
            "http",
            None,
        ),
        ("https://faß.de", "https://xn--fa-hia.de", "xn--fa-hia.de", "https", None),
        (
            "https://βόλος.com:443",
            "https://xn--nxasmm1c.com:443",
            "xn--nxasmm1c.com",
            "https",
            443,
        ),
        (
            "http://ශ්‍රී.com:444",
            "http://xn--10cl1a0b660p.com:444",
            "xn--10cl1a0b660p.com",
            "http",
            444,
        ),
        (
            "https://نامه‌ای.com:4433",
            "https://xn--mgba3gch31f060k.com:4433",
            "xn--mgba3gch31f060k.com",
            "https",
            4433,
        ),
    ],
    ids=[
        "http_with_port",
        "unicode_tr46_compat",
        "https_without_port",
        "https_with_port",
        "http_with_custom_port",
        "https_with_custom_port",
    ],
)
def test_idna_url(given, idna, host, scheme, port):
    url = httpx.URL(given)
    assert url == httpx.URL(idna)
    assert url.host == host
    assert url.scheme == scheme
    assert url.port == port


def test_url():
    url = httpx.URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
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

    new = url.copy_with(scheme="http", port=None)
    assert new == httpx.URL("http://example.org/path/to/somewhere?abc=123#anchor")
    assert new.scheme == "http"


def test_url_eq_str():
    url = httpx.URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url == "https://example.org:123/path/to/somewhere?abc=123#anchor"
    assert str(url) == url


def test_url_params():
    url = httpx.URL("https://example.org:123/path/to/somewhere", params={"a": "123"})
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"

    url = httpx.URL(
        "https://example.org:123/path/to/somewhere?b=456", params={"a": "123"}
    )
    assert str(url) == "https://example.org:123/path/to/somewhere?b=456&a=123"


def test_url_join():
    """
    Some basic URL joining tests.
    """
    url = httpx.URL("https://example.org:123/path/to/somewhere")
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

    url = httpx.URL("http://example.com/b/c/d;p?q")

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
        httpx.URL("http://example.org:123/path/to/somewhere"),
        httpx.URL("http://example.org:123/path/to/somewhere/else"),
    )

    url_set = set(urls)

    assert all(url in urls for url in url_set)


def test_url_copywith_for_authority():
    copy_with_kwargs = {
        "username": "username",
        "password": "password",
        "port": 444,
        "host": "example.net",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    for k, v in copy_with_kwargs.items():
        assert getattr(new, k) == v
    assert str(new) == "https://username:password@example.net:444"


def test_url_copywith_for_userinfo():
    copy_with_kwargs = {
        "username": "tom@example.org",
        "password": "abc123@ %",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://tom%40example.org:abc123%40%20%25@example.org"
    assert new.username == "tom@example.org"
    assert new.password == "abc123@ %"


def test_url_invalid():
    with pytest.raises(httpx.InvalidURL):
        httpx.URL("https://😇/")
