from httpx import Client, Cookies, Headers


def test_client_headers():
    client = Client()
    client.headers = {"a": "b"}
    assert isinstance(client.headers, Headers)
    assert client.headers["A"] == "b"


def test_client_cookies():
    client = Client()
    client.cookies = Cookies({"a": "b"})
    assert isinstance(client.cookies, Cookies)
    mycookies = list(client.cookies.jar)
    assert len(mycookies) == 1
    assert mycookies[0].name == "a" and mycookies[0].value == "b"
