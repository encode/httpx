from ..concurrency.base import ConcurrencyBackend
from ..config import (
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    HTTPVersionTypes,
    PoolLimits,
    SSLConfig,
    TimeoutTypes,
    VerifyTypes,
)
from ..exceptions import ProxyError
from ..models import URL, AsyncRequest, Headers, HeaderTypes, Origin, URLTypes
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
        http_versions: HTTPVersionTypes = None,
        backend: ConcurrencyBackend = None,
    ):

        super(HTTPTunnelProxy, self).__init__(
            verify=verify,
            cert=cert,
            timeout=timeout,
            pool_limits=pool_limits,
            http_versions=http_versions,
            backend=backend,
        )

        self.proxy_url = URL(proxy_url)
        self.proxy_headers = Headers(proxy_headers)

    async def acquire_connection(self, origin: Origin) -> HTTPConnection:

        # See if we have a connection that is already tunneled
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
                http_versions=["HTTP/1.1"],  # Short-lived 'connection'
                release_func=self.release_connection,
            )
            self.active_connections.add(connection)

            # See if our tunnel has been opened successfully
            proxy_response = await connection.send(proxy_request)
            await proxy_response.read()
            if not 200 <= proxy_response.status_code <= 299:
                self.max_connections.release()
                raise ProxyError(
                    f"Non-2XX response received from HTTP proxy ({proxy_response.status_code})",
                    request=proxy_request,
                    response=proxy_response,
                )

            # After we receive the 2XX response from the proxy that our
            # tunnel is open we switch the connection's origin
            # to the original so the tunnel can be re-used.
            connection.origin = origin

            # If we need to start TLS again for the target server
            # we need to pull the TCP stream off the internal
            # HTTP connection object and run start_tls()
            if origin.is_ssl:
                http_connection = connection.h11_connection
                assert http_connection is not None

                stream = http_connection.stream
                ssl_config = SSLConfig(cert=self.cert, verify=self.verify)
                timeout = connection.timeout
                ssl_context = await connection.get_ssl_context(ssl_config)
                assert ssl_context is not None

                stream = await self.backend.start_tls(
                    stream=stream,
                    hostname=origin.host,
                    ssl_context=ssl_context,
                    timeout=timeout,
                )
                http_connection.stream = stream

        else:
            self.active_connections.add(connection)

        return connection

    def __repr__(self) -> str:
        return (
            f"HTTPTunnelProxy(proxy_url={self.proxy_url!r} "
            f"proxy_headers={self.proxy_headers})"
        )
