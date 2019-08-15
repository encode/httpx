from ..config import (
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    PoolLimits,
    TimeoutTypes,
    VerifyTypes,
)
from ..exceptions import ProxyError
from ..interfaces import ConcurrencyBackend, HeaderTypes, URLTypes
from ..models import URL, AsyncRequest, Headers, Origin
from .connection import HTTPConnection
from .connection_pool import ConnectionPool


class HTTPTunnelProxy(ConnectionPool):
    """A proxy that uses the 'CONNECT' method to create a
    TCP tunnel for HTTP requests and responses.
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

        super(HTTPTunnelProxy, self).__init__(
            verify=verify,
            cert=cert,
            timeout=timeout,
            pool_limits=pool_limits,
            backend=backend,
        )

        self.proxy_url = URL(proxy_url)
        self.proxy_headers = Headers(proxy_headers)

    async def acquire_connection(self, origin: Origin) -> HTTPConnection:

        # See if we already have a connection that is already tunneled
        connection = self.active_connections.pop_by_origin(origin, http2_only=True)
        if connection is None:
            connection = self.keepalive_connections.pop_by_origin(origin)

        if connection is not None and connection.is_connection_dropped():
            connection = None

        # Create a new HTTP tunnel for that origin
        if connection is None:

            # Set the default headers that a proxy needs: 'Host', and 'Accept'.
            # We don't allow users to control 'Host' but do let them override 'Accept'.
            proxy_headers = self.proxy_headers.copy()
            proxy_headers["Host"] = f"{origin.host}:{origin.port}"
            proxy_headers.setdefault("Accept", "*/*")

            proxy_request = AsyncRequest(
                method="CONNECT", url=self.proxy_url, headers=proxy_headers
            )

            await self.max_connections.acquire()

            connection = HTTPConnection(
                self.proxy_url.origin,
                verify=self.verify,
                cert=self.cert,
                timeout=self.timeout,
                backend=self.backend,
                release_func=self.release_connection,
            )

            # See if our tunnel has been opened successfully
            proxy_response = await connection.send(proxy_request)
            if not 200 <= proxy_response.status_code <= 299:
                self.max_connections.release()
                raise ProxyError(
                    "Non-2XX response received from HTTP proxy",
                    request=proxy_request,
                    response=proxy_response,
                )

            # After we receive the 2XX response from the proxy that our
            # tunnel is open we switch the connection's origin
            # to the original so the tunnel can be re-used.
            connection.origin = origin

        self.active_connections.add(connection)
        return connection

    def __repr__(self) -> str:
        return (
            f"HTTPTunnelProxy(proxy_url={self.proxy_url!r} "
            f"proxy_headers={self.proxy_headers})"
        )
