import enum
import typing
import warnings
from base64 import b64encode

from .._backends.base import ConcurrencyBackend
from .._config import (
    DEFAULT_POOL_LIMITS,
    CertTypes,
    PoolLimits,
    SSLConfig,
    Timeout,
    VerifyTypes,
)
from .._exceptions import ProxyError
from .._models import URL, Headers, HeaderTypes, Origin, Request, Response, URLTypes
from .._utils import get_logger
from .connection import HTTPConnection
from .connection_pool import ConnectionPool

logger = get_logger(__name__)


class HTTPProxyMode(enum.Enum):
    # This enum is pending deprecation in order to reduce API surface area,
    # but is currently still around for 0.8 backwards compat.
    DEFAULT = "DEFAULT"
    FORWARD_ONLY = "FORWARD_ONLY"
    TUNNEL_ONLY = "TUNNEL_ONLY"


DEFAULT_MODE = "DEFAULT"
FORWARD_ONLY = "FORWARD_ONLY"
TUNNEL_ONLY = "TUNNEL_ONLY"


class HTTPProxy(ConnectionPool):
    """A proxy that sends requests to the recipient server
    on behalf of the connecting client.
    """

    def __init__(
        self,
        proxy_url: URLTypes,
        *,
        proxy_headers: HeaderTypes = None,
        proxy_mode: str = "DEFAULT",
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        http2: bool = False,
        backend: typing.Union[str, ConcurrencyBackend] = "auto",
    ):

        if isinstance(proxy_mode, HTTPProxyMode):  # pragma: nocover
            warnings.warn(
                "The 'HTTPProxyMode' enum is pending deprecation. "
                "Use a plain string instead. proxy_mode='FORWARD_ONLY', or "
                "proxy_mode='TUNNEL_ONLY'."
            )
            proxy_mode = proxy_mode.value
        assert proxy_mode in ("DEFAULT", "FORWARD_ONLY", "TUNNEL_ONLY")

        self.tunnel_ssl = SSLConfig(
            verify=verify, cert=cert, trust_env=trust_env, http2=False
        )

        super(HTTPProxy, self).__init__(
            verify=verify,
            cert=cert,
            pool_limits=pool_limits,
            backend=backend,
            trust_env=trust_env,
            http2=http2,
        )

        self.proxy_url = URL(proxy_url)
        self.proxy_mode = proxy_mode
        self.proxy_headers = Headers(proxy_headers)

        url = self.proxy_url
        if url.username or url.password:
            self.proxy_headers.setdefault(
                "Proxy-Authorization",
                self.build_auth_header(url.username, url.password),
            )
            # Remove userinfo from the URL authority, e.g.:
            # 'username:password@proxy_host:proxy_port' -> 'proxy_host:proxy_port'
            credentials, _, authority = url.authority.rpartition("@")
            self.proxy_url = url.copy_with(authority=authority)

    def build_auth_header(self, username: str, password: str) -> str:
        userpass = (username.encode("utf-8"), password.encode("utf-8"))
        token = b64encode(b":".join(userpass)).decode().strip()
        return f"Basic {token}"

    async def acquire_connection(
        self, origin: Origin, timeout: Timeout = None
    ) -> HTTPConnection:
        if self.should_forward_origin(origin):
            logger.trace(
                f"forward_connection proxy_url={self.proxy_url!r} origin={origin!r}"
            )
            return await super().acquire_connection(Origin(self.proxy_url), timeout)
        else:
            logger.trace(
                f"tunnel_connection proxy_url={self.proxy_url!r} origin={origin!r}"
            )
            return await self.tunnel_connection(origin, timeout)

    async def tunnel_connection(
        self, origin: Origin, timeout: Timeout = None
    ) -> HTTPConnection:
        """Creates a new HTTPConnection via the CONNECT method
        usually reserved for proxying HTTPS connections.
        """
        connection = self.pop_connection(origin)

        if connection is None:
            connection = await self.request_tunnel_proxy_connection(origin)

            # After we receive the 2XX response from the proxy that our
            # tunnel is open we switch the connection's origin
            # to the original so the tunnel can be re-used.
            self.active_connections.remove(connection)
            connection.origin = origin
            self.active_connections.add(connection)

            await connection.tunnel_start_tls(
                origin=origin, proxy_url=self.proxy_url, timeout=timeout,
            )
        else:
            self.active_connections.add(connection)

        return connection

    async def request_tunnel_proxy_connection(self, origin: Origin) -> HTTPConnection:
        """Creates an HTTPConnection by setting up a TCP tunnel"""
        proxy_headers = self.proxy_headers.copy()
        proxy_headers.setdefault("Accept", "*/*")
        proxy_request = Request(
            method="CONNECT", url=self.proxy_url.copy_with(), headers=proxy_headers
        )
        proxy_request.url.full_path = f"{origin.host}:{origin.port}"

        await self.max_connections.acquire()

        connection = HTTPConnection(
            Origin(self.proxy_url),
            ssl=self.tunnel_ssl,
            backend=self.backend,
            release_func=self.release_connection,
        )
        self.active_connections.add(connection)

        # See if our tunnel has been opened successfully
        proxy_response = await connection.send(proxy_request)
        logger.trace(
            f"tunnel_response "
            f"proxy_url={self.proxy_url!r} "
            f"origin={origin!r} "
            f"response={proxy_response!r}"
        )
        if not (200 <= proxy_response.status_code <= 299):
            await proxy_response.aread()
            raise ProxyError(
                f"Non-2XX response received from HTTP proxy "
                f"({proxy_response.status_code})",
                request=proxy_request,
                response=proxy_response,
            )
        else:
            # Hack to ingest the response, without closing it.
            async for chunk in proxy_response._raw_stream:
                pass

        return connection

    def should_forward_origin(self, origin: Origin) -> bool:
        """Determines if the given origin should
        be forwarded or tunneled. If 'proxy_mode' is 'DEFAULT'
        then the proxy will forward all 'HTTP' requests and
        tunnel all 'HTTPS' requests.
        """
        return (
            self.proxy_mode == DEFAULT_MODE and not origin.is_ssl
        ) or self.proxy_mode == FORWARD_ONLY

    async def send(self, request: Request, timeout: Timeout = None) -> Response:
        if self.should_forward_origin(Origin(request.url)):
            # Change the request to have the target URL
            # as its full_path and switch the proxy URL
            # for where the request will be sent.
            target_url = str(request.url)
            request.url = self.proxy_url.copy_with()
            request.url.full_path = target_url
            for name, value in self.proxy_headers.items():
                request.headers.setdefault(name, value)

        return await super().send(request=request, timeout=timeout)

    def __repr__(self) -> str:
        return (
            f"HTTPProxy(proxy_url={self.proxy_url!r} "
            f"proxy_headers={self.proxy_headers!r} "
            f"proxy_mode={self.proxy_mode!r})"
        )
