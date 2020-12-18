"""
Default HTTP transports, with nicely configured defaults.
"""
import httpcore

from .._config import DEFAULT_LIMITS, Limits, create_ssl_context
from .._types import CertTypes, VerifyTypes


def create_default_transport(
    verify: VerifyTypes = True,
    cert: CertTypes = None,
    http2: bool = False,
    limits: Limits = DEFAULT_LIMITS,
    trust_env: bool = True,
    uds: str = None,
    local_address: str = None,
    retries: int = 0,
) -> httpcore.SyncHTTPTransport:
    ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

    return httpcore.SyncConnectionPool(
        ssl_context=ssl_context,
        max_connections=limits.max_connections,
        max_keepalive_connections=limits.max_keepalive_connections,
        keepalive_expiry=limits.keepalive_expiry,
        http2=http2,
        uds=uds,
        local_address=local_address,
        retries=retries,
    )


def create_default_async_transport(
    verify: VerifyTypes = True,
    cert: CertTypes = None,
    http2: bool = False,
    limits: Limits = DEFAULT_LIMITS,
    trust_env: bool = True,
    uds: str = None,
    local_address: str = None,
    retries: int = 0,
    backend: str = "auto",
) -> httpcore.AsyncConnectionPool:
    ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

    return httpcore.AsyncConnectionPool(
        ssl_context=ssl_context,
        max_connections=limits.max_connections,
        max_keepalive_connections=limits.max_keepalive_connections,
        keepalive_expiry=limits.keepalive_expiry,
        http2=http2,
        uds=uds,
        local_address=local_address,
        retries=retries,
        backend=backend,
    )
