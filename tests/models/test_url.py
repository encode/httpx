from httpcore import URL


def test_idna_url():
    url = URL("http://中国.icom.museum:80/")
    assert url == URL("http://xn--fiqs8s.icom.museum:80/")
    assert url.host == "xn--fiqs8s.icom.museum"
