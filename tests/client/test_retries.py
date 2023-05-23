"""
Connection retries are implemeted at the transport layer in `httpcore` but exposed
as `connect_retries` in httpx clients for convenience.
"""
import httpx


def test_client_defaults_to_zero_retries_on_transport_pool():
    client = httpx.Client()

    assert client._transport._pool._retries == 0


def test_client_sets_connect_retries_on_transport_pool():
    client = httpx.Client(connect_retries=3)

    assert client._transport._pool._retries == 3


def test_client_sets_connect_retries_on_proxy_transport_pool():
    client = httpx.Client(
        connect_retries=3, proxies={"http://example.net": "http://[::1]"}
    )

    assert (
        client._transport_for_url(httpx.URL("http://example.net"))._pool._retries == 3
    )
    assert (
        client._transport_for_url(httpx.URL("http://example.com"))._pool._retries == 3
    )


def test_client_does_not_set_retries_on_user_provided_transport():
    transport = httpx.HTTPTransport()
    client = httpx.Client(transport=transport, connect_retries=3)

    assert client._transport._pool._retries == 0
