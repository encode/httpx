from ..concurrency.base import ConcurrencyBackend
from ..config import (
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    PoolLimits,
    TimeoutTypes,
    VerifyTypes,
)
from ..models import (
    URL,
    AsyncRequest,
    AsyncResponse,
    Headers,
    HeaderTypes,
    Origin,
    URLTypes,
)
from .connection import HTTPConnection
from .connection_pool import ConnectionPool


class HTTPForwardingProxy(ConnectionPool):
    """A proxy that sends requests to the recipient server
    on behalf of the connecting client. Not recommended for HTTPS.
    """

    def __init__(
        self,
        proxy_url: URLTypes,
        *,
        proxy_headers: HeaderTypes = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        backend: ConcurrencyBackend = None,
    ):

        super(HTTPForwardingProxy, self).__init__(
            verify=verify,
            cert=cert,
            timeout=timeout,
            pool_limits=pool_limits,
            backend=backend,
        )

        self.proxy_url = URL(proxy_url)
        self.proxy_headers = Headers(proxy_headers)

    async def acquire_connection(self, origin: Origin) -> HTTPConnection:
        return await super().acquire_connection(self.proxy_url.origin)

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:

        # Change the request to have the target URL
        # as its full_path and switch the proxy URL
        # for where the request will be sent.
        target_url = str(request.url)
        request.url = self.proxy_url.copy_with()
        request.url.full_path = target_url
        for name, value in self.proxy_headers.items():
            request.headers.setdefault(name, value)

        return await super().send(
            request=request, verify=verify, cert=cert, timeout=timeout
        )

    def __repr__(self) -> str:
        return (
            f"HTTPTunnelProxy(proxy_url={self.proxy_url!r} "
            f"proxy_headers={self.proxy_headers})"
        )
