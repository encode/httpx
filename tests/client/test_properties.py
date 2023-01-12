import httpx


def test_client_base_url():
    client = httpx.Client()
    client.base_url = "https://www.example.org/"  # type: ignore
    assert isinstance(client.base_url, httpx.URL)
    assert client.base_url == "https://www.example.org/"


def test_client_base_url_without_trailing_slash():
    client = httpx.Client()
    client.base_url = "https://www.example.org/path"  # type: ignore
    assert isinstance(client.base_url, httpx.URL)
    assert client.base_url == "https://www.example.org/path/"


def test_client_base_url_with_trailing_slash():
    client = httpx.Client()
    client.base_url = "https://www.example.org/path/"  # type: ignore
    assert isinstance(client.base_url, httpx.URL)
    assert client.base_url == "https://www.example.org/path/"


def test_client_headers():
    client = httpx.Client()
    client.headers = {"a": "b"}  # type: ignore
    assert isinstance(client.headers, httpx.Headers)
    assert client.headers["A"] == "b"


def test_client_cookies():
    client = httpx.Client()
    client.cookies = {"a": "b"}  # type: ignore
    assert isinstance(client.cookies, httpx.Cookies)
    mycookies = list(client.cookies.jar)
    assert len(mycookies) == 1
    assert mycookies[0].name == "a" and mycookies[0].value == "b"


def test_client_timeout():
    expected_timeout = 12.0
    client = httpx.Client()

    client.timeout = expected_timeout  # type: ignore

    assert isinstance(client.timeout, httpx.Timeout)
    assert client.timeout.connect == expected_timeout
    assert client.timeout.read == expected_timeout
    assert client.timeout.write == expected_timeout
    assert client.timeout.pool == expected_timeout


def test_client_event_hooks():
    def on_request(request):
        pass  # pragma: no cover

    client = httpx.Client()
    client.event_hooks = {"request": [on_request]}
    assert client.event_hooks == {"request": [on_request], "response": []}


def test_client_trust_env():
    client = httpx.Client()
    assert client.trust_env

    client = httpx.Client(trust_env=False)
    assert not client.trust_env
