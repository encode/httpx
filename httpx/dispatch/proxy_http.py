import enum

from ..concurrency.base import ConcurrencyBackend
from ..config import (
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    PoolLimits,
    SSLConfig,
    TimeoutTypes,
    VerifyTypes,
)
from ..exceptions import ProxyError
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


class HTTPProxyMode(enum.Enum):
    DEFAULT = "DEFAULT"
    FORWARD_ONLY = "FORWARD_ONLY"
    TUNNEL_ONLY = "TUNNEL_ONLY"


class HTTPProxy(ConnectionPool):
    """A proxy that sends requests to the recipient server
    on behalf of the connecting client. Not recommended for HTTPS.
    """

    def __init__(
        self,
        proxy_url: URLTypes,
        *,
        proxy_headers: HeaderTypes = None,
        proxy_mode: HTTPProxyMode = HTTPProxyMode.DEFAULT,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        backend: ConcurrencyBackend = None,
    ):

        super(HTTPProxy, self).__init__(
            verify=verify,
            cert=cert,
            timeout=timeout,
            pool_limits=pool_limits,
            backend=backend,
        )

        self.proxy_url = URL(proxy_url)
        self.proxy_mode = proxy_mode
        self.proxy_headers = Headers(proxy_headers)

    async def acquire_connection(self, origin: Origin) -> HTTPConnection:
        if self.should_forward_origin(origin):
            return await super().acquire_connection(self.proxy_url.origin)
        else:
            return await self.tunnel_connection(origin)

    async def tunnel_connection(self, origin: Origin) -> HTTPConnection:
        """Creates a new HTTPConnection via the CONNECT method
        usually reserved for proxying HTTPS connections.
        """
        connection = self.pop_connection(origin)

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
                raise ProxyError(
                    f"Non-2XX response received from HTTP proxy "
                    f"({proxy_response.status_code})",
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

    def should_forward_origin(self, origin: Origin) -> bool:
        """Determines if the given origin should
        be forwarded or tunneled. If 'proxy_mode' is 'DEFAULT'
        then the proxy will forward all 'HTTP' requests and
        tunnel all 'HTTPS' requests.
        """
        return (
            self.proxy_mode == HTTPProxyMode.DEFAULT and not origin.is_ssl
        ) or self.proxy_mode == HTTPProxyMode.FORWARD_ONLY

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:

        if self.should_forward_origin(request.url.origin):
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
            f"HTTPProxy(proxy_url={self.proxy_url!r} "
            f"proxy_headers={self.proxy_headers!r} "
            f"proxy_mode={self.proxy_mode!r})"
        )
