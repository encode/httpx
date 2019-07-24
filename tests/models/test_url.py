from httpx import URL


def test_idna_url():
    url = URL("http://中国.icom.museum:80/")
    assert url == URL("http://xn--fiqs8s.icom.museum:80/")
    assert url.host == "xn--fiqs8s.icom.museum"


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


def test_url__params():
    url = URL("https://example.org:123/path/to/somewhere", params={"a": "123"})
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"

    url = URL("https://example.org:123/path/to/somewhere?b=456", params={"a": "123"})
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"


def test_url_set():
    urls = (
        URL("http://example.org:123/path/to/somewhere"),
        URL("http://example.org:123/path/to/somewhere/else"),
    )

    url_set = set(urls)

    assert all(url in urls for url in url_set)
