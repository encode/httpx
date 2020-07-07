from httpx import AsyncClient, Cookies, Headers


def test_client_headers():
    client = AsyncClient()
    client.headers = {"a": "b"}  # type: ignore
    assert isinstance(client.headers, Headers)
    assert client.headers["A"] == "b"


def test_client_cookies():
    client = AsyncClient()
    client.cookies = {"a": "b"}  # type: ignore
    assert isinstance(client.cookies, Cookies)
    mycookies = list(client.cookies.jar)
    assert len(mycookies) == 1
    assert mycookies[0].name == "a" and mycookies[0].value == "b"
