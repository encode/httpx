from httpcore import URL


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
    assert repr(url) == "URL('https://example.org:123/path/to/somewhere?abc=123#anchor')"

    new = url.copy_with(scheme="http")
    assert new == URL("http://example.org:123/path/to/somewhere?abc=123#anchor")
    assert new.scheme == "http"
