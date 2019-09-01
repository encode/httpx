import os

import pytest

import httpx


def test_proxies_not_set():
    client = httpx.Client()

    assert client.proxies == {}


def test_proxies_single_url():
    client = httpx.Client(proxies="http://127.0.0.1:3000")

    assert len(client.proxies) == 1
    assert isinstance(client.proxies["all"], httpx.HTTPProxy)
    assert client.proxies["all"].proxy_url == "http://127.0.0.1:3000"
    assert client.proxies["all"].proxy_mode == httpx.HTTPProxyMode.DEFAULT


def test_proxies_scheme_url():
    client = httpx.Client(proxies={"http": "http://127.0.0.1:3000"})

    assert len(client.proxies) == 1
    assert isinstance(client.proxies["http"], httpx.HTTPProxy)
    assert client.proxies["http"].proxy_url == "http://127.0.0.1:3000"
    assert client.proxies["http"].proxy_mode == httpx.HTTPProxyMode.DEFAULT


@pytest.mark.parametrize("kwargs", [{}, {"trust_env": True}])
def test_proxies_set_from_environ_trust_env(kwargs):
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:3000"

    client = httpx.Client(*kwargs)

    assert len(client.proxies) == 1
    assert isinstance(client.proxies["http"], httpx.HTTPProxy)
    assert client.proxies["http"].proxy_url == "http://127.0.0.1:3000"
    assert client.proxies["http"].proxy_mode == httpx.HTTPProxyMode.DEFAULT


@pytest.mark.parametrize("environ_key", ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"])
def test_proxies_set_from_environ_variations(environ_key):
    os.environ[environ_key] = "http://127.0.0.1:3000"
    proxy_key = environ_key.lower().split("_", 1)[0]

    client = httpx.Client()

    assert len(client.proxies) == 1
    assert isinstance(client.proxies[proxy_key], httpx.HTTPProxy)
    assert client.proxies[proxy_key].proxy_url == "http://127.0.0.1:3000"
    assert client.proxies[proxy_key].proxy_mode == httpx.HTTPProxyMode.DEFAULT


def test_proxies_set_from_environ_no_trust_env():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:3000"

    client = httpx.Client(trust_env=False)

    assert len(client.proxies) == 0


def test_proxies_authentication_in_url():
    client = httpx.Client(proxies="http://user:password@127.0.0.1:3000")
    assert len(client.proxies) == 1
    assert isinstance(client.proxies["all"], httpx.HTTPProxy)
    assert client.proxies["all"].proxy_url == "http://127.0.0.1:3000"
    assert client.proxies["all"].proxy_headers == {"Proxy-Authorization": ""}
