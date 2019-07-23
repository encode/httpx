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


def test_url_params():
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


def test_url_div():
    url = URL("http://www.example.com/path/to/file.ext?query#fragment")

    assert str("http://example.org" / url) == str(url)
    assert str("http://example.org/over/the/rainbow" / url) == str(url)

    assert (
        str(url / "https://secure.example.com/path")
        == "https://secure.example.com/path"
    )
    assert str(url / "/changed/path") == "http://www.example.com/changed/path"
    assert (
        str(URL("http://example.com/base/") / "path/to/file")
        == "http://example.com/base/path/to/file"
    )
    assert (
        str(URL("http://example.com/no/trailing/slash/base") / "path/to/file")
        == "http://example.com/no/trailing/slash/path/to/file"
    )
    assert (
        str(
            URL("http://example.com/path/?q")
            / URL("http://localhost/app/?q")
            / URL("to/content", allow_relative=True)
        )
        == "http://localhost/app/to/content"
    )

    assert (
        str(URL("http://example.com/name/") / "\u65e5\u672c\u8a9e/\u540d\u524d")
        == "http://example.com/name/%E6%97%A5%E6%9C%AC%E8%AA%9E/%E5%90%8D%E5%89%8D"
    )

    url = URL("s3://mybucket") / "some_folder/123_2017-10-30T18:43:11.csv.gz"
    assert str(url) == "s3://mybucket/some_folder/123_2017-10-30T18:43:11.csv.gz"
