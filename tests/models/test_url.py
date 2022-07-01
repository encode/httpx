import pytest

import httpx


@pytest.mark.parametrize(
    "given,idna,host,raw_host,scheme,port",
    [
        (
            "http://中国.icom.museum:80/",
            "http://xn--fiqs8s.icom.museum:80/",
            "中国.icom.museum",
            b"xn--fiqs8s.icom.museum",
            "http",
            None,
        ),
        (
            "http://Königsgäßchen.de",
            "http://xn--knigsgchen-b4a3dun.de",
            "königsgäßchen.de",
            b"xn--knigsgchen-b4a3dun.de",
            "http",
            None,
        ),
        (
            "https://faß.de",
            "https://xn--fa-hia.de",
            "faß.de",
            b"xn--fa-hia.de",
            "https",
            None,
        ),
        (
            "https://βόλος.com:443",
            "https://xn--nxasmm1c.com:443",
            "βόλος.com",
            b"xn--nxasmm1c.com",
            "https",
            None,
        ),
        (
            "http://ශ්‍රී.com:444",
            "http://xn--10cl1a0b660p.com:444",
            "ශ්‍රී.com",
            b"xn--10cl1a0b660p.com",
            "http",
            444,
        ),
        (
            "https://نامه‌ای.com:4433",
            "https://xn--mgba3gch31f060k.com:4433",
            "نامه‌ای.com",
            b"xn--mgba3gch31f060k.com",
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
def test_idna_url(given, idna, host, raw_host, scheme, port):
    url = httpx.URL(given)
    assert url == httpx.URL(idna)
    assert url.host == host
    assert url.raw_host == raw_host
    assert url.scheme == scheme
    assert url.port == port


def test_url():
    url = httpx.URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url.scheme == "https"
    assert url.host == "example.org"
    assert url.port == 123
    assert url.path == "/path/to/somewhere"
    assert url.query == b"abc=123"
    assert url.raw_path == b"/path/to/somewhere?abc=123"
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
    assert url.params == httpx.QueryParams({"a": "123"})

    url = httpx.URL(
        "https://example.org:123/path/to/somewhere?b=456", params={"a": "123"}
    )
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"
    assert url.params == httpx.QueryParams({"a": "123"})


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


def test_url_set_param_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_set_param("a", "456") == "https://example.org:123/?a=456"


def test_url_add_param_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_add_param("a", "456") == "https://example.org:123/?a=123&a=456"


def test_url_remove_param_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_remove_param("a") == "https://example.org:123/"


def test_url_merge_params_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_merge_params({"b": "456"}) == "https://example.org:123/?a=123&b=456"


def test_relative_url_join():
    url = httpx.URL("/path/to/somewhere")
    assert url.join("/somewhere-else") == "/somewhere-else"
    assert url.join("somewhere-else") == "/path/to/somewhere-else"
    assert url.join("../somewhere-else") == "/path/somewhere-else"
    assert url.join("../../somewhere-else") == "/somewhere-else"


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


def test_url_copywith_authority_subcomponents():
    copy_with_kwargs = {
        "username": "username",
        "password": "password",
        "port": 444,
        "host": "example.net",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://username:password@example.net:444"


def test_url_copywith_netloc():
    copy_with_kwargs = {
        "netloc": b"example.net:444",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://example.net:444"


def test_url_copywith_userinfo_subcomponents():
    copy_with_kwargs = {
        "username": "tom@example.org",
        "password": "abc123@ %",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://tom%40example.org:abc123%40%20%25@example.org"
    assert new.username == "tom@example.org"
    assert new.password == "abc123@ %"
    assert new.userinfo == b"tom%40example.org:abc123%40%20%25"


def test_url_copywith_invalid_component():
    url = httpx.URL("https://example.org")
    with pytest.raises(TypeError):
        url.copy_with(pathh="/incorrect-spelling")
    with pytest.raises(TypeError):
        url.copy_with(userinfo="should be bytes")


def test_url_copywith_urlencoded_path():
    url = httpx.URL("https://example.org")
    url = url.copy_with(path="/path to somewhere")
    assert url.path == "/path to somewhere"
    assert url.query == b""
    assert url.raw_path == b"/path%20to%20somewhere"


def test_url_copywith_query():
    url = httpx.URL("https://example.org")
    url = url.copy_with(query=b"a=123")
    assert url.path == "/"
    assert url.query == b"a=123"
    assert url.raw_path == b"/?a=123"


def test_url_copywith_raw_path():
    url = httpx.URL("https://example.org")
    url = url.copy_with(raw_path=b"/some/path")
    assert url.path == "/some/path"
    assert url.query == b""
    assert url.raw_path == b"/some/path"

    url = httpx.URL("https://example.org")
    url = url.copy_with(raw_path=b"/some/path?")
    assert url.path == "/some/path"
    assert url.query == b""
    assert url.raw_path == b"/some/path?"

    url = httpx.URL("https://example.org")
    url = url.copy_with(raw_path=b"/some/path?a=123")
    assert url.path == "/some/path"
    assert url.query == b"a=123"
    assert url.raw_path == b"/some/path?a=123"


def test_url_copywith_security():
    """
    Prevent unexpected changes on URL after calling copy_with (CVE-2021-41945)
    """
    url = httpx.URL("https://u:p@[invalid!]//evilHost/path?t=w#tw")
    original_scheme = url.scheme
    original_userinfo = url.userinfo
    original_netloc = url.netloc
    original_raw_path = url.raw_path
    original_query = url.query
    original_fragment = url.fragment
    url = url.copy_with()
    assert url.scheme == original_scheme
    assert url.userinfo == original_userinfo
    assert url.netloc == original_netloc
    assert url.raw_path == original_raw_path
    assert url.query == original_query
    assert url.fragment == original_fragment

    url = httpx.URL("https://u:p@[invalid!]//evilHost/path?t=w#tw")
    original_scheme = url.scheme
    original_netloc = url.netloc
    original_raw_path = url.raw_path
    original_query = url.query
    original_fragment = url.fragment
    url = url.copy_with(userinfo=b"")
    assert url.scheme == original_scheme
    assert url.userinfo == b""
    assert url.netloc == original_netloc
    assert url.raw_path == original_raw_path
    assert url.query == original_query
    assert url.fragment == original_fragment

    url = httpx.URL("https://example.com/path?t=w#tw")
    original_userinfo = url.userinfo
    original_netloc = url.netloc
    original_raw_path = url.raw_path
    original_query = url.query
    original_fragment = url.fragment
    bad = "https://xxxx:xxxx@xxxxxxx/xxxxx/xxx?x=x#xxxxx"
    url = url.copy_with(scheme=bad)
    assert url.scheme == bad
    assert url.userinfo == original_userinfo
    assert url.netloc == original_netloc
    assert url.raw_path == original_raw_path
    assert url.query == original_query
    assert url.fragment == original_fragment


def test_url_invalid():
    with pytest.raises(httpx.InvalidURL):
        httpx.URL("https://😇/")


def test_url_invalid_type():
    class ExternalURLClass:  # representing external URL class
        pass

    with pytest.raises(TypeError):
        httpx.URL(ExternalURLClass())  # type: ignore


def test_url_with_empty_query():
    """
    URLs with and without a trailing `?` but an empty query component
    should preserve the information on the raw path.
    """
    url = httpx.URL("https://www.example.com/path")
    assert url.path == "/path"
    assert url.query == b""
    assert url.raw_path == b"/path"

    url = httpx.URL("https://www.example.com/path?")
    assert url.path == "/path"
    assert url.query == b""
    assert url.raw_path == b"/path?"


def test_url_with_url_encoded_path():
    url = httpx.URL("https://www.example.com/path%20to%20somewhere")
    assert url.path == "/path to somewhere"
    assert url.query == b""
    assert url.raw_path == b"/path%20to%20somewhere"


def test_ipv6_url():
    url = httpx.URL("http://[::ffff:192.168.0.1]:5678/")

    assert url.host == "::ffff:192.168.0.1"
    assert url.netloc == b"[::ffff:192.168.0.1]:5678"


@pytest.mark.parametrize(
    "url_str",
    [
        "http://127.0.0.1:1234",
        "http://example.com:1234",
        "http://[::ffff:127.0.0.1]:1234",
    ],
)
@pytest.mark.parametrize("new_host", ["[::ffff:192.168.0.1]", "::ffff:192.168.0.1"])
def test_ipv6_url_copy_with_host(url_str, new_host):
    url = httpx.URL(url_str).copy_with(host=new_host)

    assert url.host == "::ffff:192.168.0.1"
    assert url.netloc == b"[::ffff:192.168.0.1]:1234"
    assert str(url) == "http://[::ffff:192.168.0.1]:1234"


@pytest.mark.parametrize("host", ["[::ffff:192.168.0.1]", "::ffff:192.168.0.1"])
def test_ipv6_url_from_raw_url(host):
    url = httpx.URL(scheme="https", host=host, port=443, path="/")

    assert url.host == "::ffff:192.168.0.1"
    assert url.netloc == b"[::ffff:192.168.0.1]"
    assert str(url) == "https://[::ffff:192.168.0.1]/"
