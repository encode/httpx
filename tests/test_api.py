from functools import partial
from unittest import mock

import pytest

import httpx


def test_get(server):
    response = httpx.get(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


def test_post(server):
    response = httpx.post(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_post_byte_iterator(server):
    def data():
        yield b"Hello"
        yield b", "
        yield b"world!"

    response = httpx.post(server.url, data=data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_options(server):
    response = httpx.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_head(server):
    response = httpx.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_put(server):
    response = httpx.put(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_patch(server):
    response = httpx.patch(server.url, data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_delete(server):
    response = httpx.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_get_invalid_url(server):
    with pytest.raises(httpx.InvalidURL):
        httpx.get("invalid://example.org")


@pytest.mark.parametrize(
    "api_method",
    [
        httpx.get,
        httpx.options,
        httpx.head,
        httpx.post,
        httpx.put,
        httpx.patch,
        httpx.delete,
        partial(httpx.request, "GET"),
    ],
)
def test_api_timeout_default(server, api_method):
    with mock.patch("httpx.api.Client.request") as mocked:
        api_method(server.url)
        assert mocked.call_args[1]["timeout"] is httpx.config.UNSET


@pytest.mark.parametrize("timeout", [10, None])
@pytest.mark.parametrize(
    "api_method",
    [
        httpx.get,
        httpx.options,
        httpx.head,
        httpx.post,
        httpx.put,
        httpx.patch,
        httpx.delete,
        partial(httpx.request, "GET"),
    ],
)
def test_api_timeout_custom(server, api_method, timeout):
    with mock.patch("httpx.api.Client.request") as mocked:
        api_method(server.url, timeout=timeout)
        assert mocked.call_args[1]["timeout"] == timeout
