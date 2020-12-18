import httpcore

import httpx


def test_default_transport() -> None:
    ssl_context = httpx.create_ssl_context(trust_env=True)
    transport = httpx.create_default_transport(verify=ssl_context)

    assert isinstance(transport, httpcore.SyncConnectionPool)

    equivalent_transport = httpcore.SyncConnectionPool(
        ssl_context=ssl_context,
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=5.0,
    )

    # Test attributes of interest only.
    for name in (
        "_ssl_context",
        "_max_connections",
        "_max_keepalive_connections",
        "_keepalive_expiry",
        "_uds",
        "_local_address",
        "_retries",
    ):
        assert getattr(transport, name) == getattr(equivalent_transport, name)


def test_default_async_transport() -> None:
    ssl_context = httpx.create_ssl_context(trust_env=True)
    transport = httpx.create_default_async_transport(verify=ssl_context)

    assert isinstance(transport, httpcore.AsyncConnectionPool)

    equivalent_transport = httpcore.AsyncConnectionPool(
        ssl_context=ssl_context,
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=5.0,
    )

    # Test attributes of interest only.
    for name in (
        "_ssl_context",
        "_max_connections",
        "_max_keepalive_connections",
        "_keepalive_expiry",
        "_uds",
        "_local_address",
        "_retries",
    ):
        assert getattr(transport, name) == getattr(equivalent_transport, name)
