"""
Custom transports, with nicely configured defaults.

The following additional keyword arguments are currently supported by httpcore...

* uds: str
* local_address: str
* retries: int
* backend: str ("auto", "asyncio", "trio", "curio", "anyio", "sync")

Example usages...

# Disable HTTP/2 on a single specfic domain.
mounts = {
    "all://": httpx.create_default_transport(http2=True),
    "all://*example.org": httpx.create_transport()
}

# Using advanced httpcore configuration, with connection retries.
transport = httpx.create_default_transport(retries=1)
client = httpx.Client(transport=transport)

# Using advanced httpcore configuration, with unix domain sockets.
transport = httpx.create_default_transport(uds="socket.uds")
client = httpx.Client(transport=transport)
"""
from typing import Any

import httpcore

from .._config import DEFAULT_LIMITS, Limits, create_ssl_context
from .._types import CertTypes, VerifyTypes


def create_default_transport(
    verify: VerifyTypes = True,
    cert: CertTypes = None,
    http2: bool = False,
    limits: Limits = DEFAULT_LIMITS,
    trust_env: bool = True,
    **kwargs: Any,
) -> httpcore.SyncConnectionPool:
    ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

    return httpcore.SyncConnectionPool(
        ssl_context=ssl_context,
        max_connections=limits.max_connections,
        max_keepalive_connections=limits.max_keepalive_connections,
        keepalive_expiry=limits.keepalive_expiry,
        http2=http2,
        **kwargs,
    )


def create_default_async_transport(
    verify: VerifyTypes = True,
    cert: CertTypes = None,
    http2: bool = False,
    limits: Limits = DEFAULT_LIMITS,
    trust_env: bool = True,
    **kwargs: Any,
) -> httpcore.AsyncConnectionPool:
    ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

    return httpcore.AsyncConnectionPool(
        ssl_context=ssl_context,
        max_connections=limits.max_connections,
        max_keepalive_connections=limits.max_keepalive_connections,
        keepalive_expiry=limits.keepalive_expiry,
        http2=http2,
        **kwargs,
    )
