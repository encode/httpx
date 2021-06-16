import os
import ssl
import typing
from base64 import b64encode
from pathlib import Path

import certifi

from ._compat import set_minimum_tls_version_1_2
from ._models import URL, Headers
from ._types import CertTypes, HeaderTypes, TimeoutTypes, URLTypes, VerifyTypes
from ._utils import get_ca_bundle_from_env, get_logger

DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    ]
)


logger = get_logger(__name__)


class UnsetType:
    pass  # pragma: nocover


UNSET = UnsetType()


def create_ssl_context(
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    trust_env: bool = True,
    http2: bool = False,
) -> ssl.SSLContext:
    return SSLConfig(
        cert=cert, verify=verify, trust_env=trust_env, http2=http2
    ).ssl_context


class SSLConfig:
    """
    SSL Configuration.
    """

    DEFAULT_CA_BUNDLE_PATH = Path(certifi.where())

    def __init__(
        self,
        *,
        cert: CertTypes = None,
        verify: VerifyTypes = True,
        trust_env: bool = True,
        http2: bool = False,
    ):
        self.cert = cert
        self.verify = verify
        self.trust_env = trust_env
        self.http2 = http2
        self.ssl_context = self.load_ssl_context()

    def load_ssl_context(self) -> ssl.SSLContext:
        logger.trace(
            f"load_ssl_context "
            f"verify={self.verify!r} "
            f"cert={self.cert!r} "
            f"trust_env={self.trust_env!r} "
            f"http2={self.http2!r}"
        )

        if self.verify:
            return self.load_ssl_context_verify()
        return self.load_ssl_context_no_verify()

    def load_ssl_context_no_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        context = self._create_default_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self._load_client_certs(context)
        return context

    def load_ssl_context_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for verified connections.
        """
        if self.trust_env and self.verify is True:
            ca_bundle = get_ca_bundle_from_env()
            if ca_bundle is not None:
                self.verify = ca_bundle

        if isinstance(self.verify, ssl.SSLContext):
            # Allow passing in our own SSLContext object that's pre-configured.
            context = self.verify
            self._load_client_certs(context)
            return context
        elif isinstance(self.verify, bool):
            ca_bundle_path = self.DEFAULT_CA_BUNDLE_PATH
        elif Path(self.verify).exists():
            ca_bundle_path = Path(self.verify)
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(self.verify)
            )

        context = self._create_default_ssl_context()
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True

        # Signal to server support for PHA in TLS 1.3. Raises an
        # AttributeError if only read-only access is implemented.
        try:
            context.post_handshake_auth = True  # type: ignore
        except AttributeError:  # pragma: nocover
            pass

        # Disable using 'commonName' for SSLContext.check_hostname
        # when the 'subjectAltName' extension isn't available.
        try:
            context.hostname_checks_common_name = False  # type: ignore
        except AttributeError:  # pragma: nocover
            pass

        if ca_bundle_path.is_file():
            logger.trace(f"load_verify_locations cafile={ca_bundle_path!s}")
            context.load_verify_locations(cafile=str(ca_bundle_path))
        elif ca_bundle_path.is_dir():
            logger.trace(f"load_verify_locations capath={ca_bundle_path!s}")
            context.load_verify_locations(capath=str(ca_bundle_path))

        self._load_client_certs(context)

        return context

    def _create_default_ssl_context(self) -> ssl.SSLContext:
        """
        Creates the default SSLContext object that's used for both verified
        and unverified connections.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        set_minimum_tls_version_1_2(context)
        context.options |= ssl.OP_NO_COMPRESSION
        context.set_ciphers(DEFAULT_CIPHERS)

        if ssl.HAS_ALPN:
            alpn_idents = ["http/1.1", "h2"] if self.http2 else ["http/1.1"]
            context.set_alpn_protocols(alpn_idents)

        if hasattr(context, "keylog_filename"):  # pragma: nocover (Available in 3.8+)
            keylogfile = os.environ.get("SSLKEYLOGFILE")
            if keylogfile and self.trust_env:
                context.keylog_filename = keylogfile  # type: ignore

        return context

    def _load_client_certs(self, ssl_context: ssl.SSLContext) -> None:
        """
        Loads client certificates into our SSLContext object
        """
        if self.cert is not None:
            if isinstance(self.cert, str):
                ssl_context.load_cert_chain(certfile=self.cert)
            elif isinstance(self.cert, tuple) and len(self.cert) == 2:
                ssl_context.load_cert_chain(certfile=self.cert[0], keyfile=self.cert[1])
            elif isinstance(self.cert, tuple) and len(self.cert) == 3:
                ssl_context.load_cert_chain(
                    certfile=self.cert[0],
                    keyfile=self.cert[1],
                    password=self.cert[2],  # type: ignore
                )


class Timeout:
    """
    Timeout configuration.

    **Usage**:

    Timeout(None)               # No timeouts.
    Timeout(5.0)                # 5s timeout on all operations.
    Timeout(None, connect=5.0)  # 5s timeout on connect, no other timeouts.
    Timeout(5.0, connect=10.0)  # 10s timeout on connect. 5s timeout elsewhere.
    Timeout(5.0, pool=None)     # No timeout on acquiring connection from pool.
                                # 5s timeout elsewhere.
    """

    def __init__(
        self,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
        *,
        connect: typing.Union[None, float, UnsetType] = UNSET,
        read: typing.Union[None, float, UnsetType] = UNSET,
        write: typing.Union[None, float, UnsetType] = UNSET,
        pool: typing.Union[None, float, UnsetType] = UNSET,
    ):
        if isinstance(timeout, Timeout):
            # Passed as a single explicit Timeout.
            assert connect is UNSET
            assert read is UNSET
            assert write is UNSET
            assert pool is UNSET
            self.connect = timeout.connect  # type: typing.Optional[float]
            self.read = timeout.read  # type: typing.Optional[float]
            self.write = timeout.write  # type: typing.Optional[float]
            self.pool = timeout.pool  # type: typing.Optional[float]
        elif isinstance(timeout, tuple):
            # Passed as a tuple.
            self.connect = timeout[0]
            self.read = timeout[1]
            self.write = None if len(timeout) < 3 else timeout[2]
            self.pool = None if len(timeout) < 4 else timeout[3]
        elif not (
            isinstance(connect, UnsetType)
            or isinstance(read, UnsetType)
            or isinstance(write, UnsetType)
            or isinstance(pool, UnsetType)
        ):
            self.connect = connect
            self.read = read
            self.write = write
            self.pool = pool
        else:
            if isinstance(timeout, UnsetType):
                raise ValueError(
                    "httpx.Timeout must either include a default, or set all "
                    "four parameters explicitly."
                )
            self.connect = timeout if isinstance(connect, UnsetType) else connect
            self.read = timeout if isinstance(read, UnsetType) else read
            self.write = timeout if isinstance(write, UnsetType) else write
            self.pool = timeout if isinstance(pool, UnsetType) else pool

    def as_dict(self) -> typing.Dict[str, typing.Optional[float]]:
        return {
            "connect": self.connect,
            "read": self.read,
            "write": self.write,
            "pool": self.pool,
        }

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.connect == other.connect
            and self.read == other.read
            and self.write == other.write
            and self.pool == other.pool
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if len({self.connect, self.read, self.write, self.pool}) == 1:
            return f"{class_name}(timeout={self.connect})"
        return (
            f"{class_name}(connect={self.connect}, "
            f"read={self.read}, write={self.write}, pool={self.pool})"
        )


class Limits:
    """
    Configuration for limits to various client behaviors.

    **Parameters:**

    * **max_connections** - The maximum number of concurrent connections that may be
            established.
    * **max_keepalive_connections** - Allow the connection pool to maintain
            keep-alive connections below this point. Should be less than or equal
            to `max_connections`.
    """

    def __init__(
        self,
        *,
        max_connections: int = None,
        max_keepalive_connections: int = None,
        keepalive_expiry: typing.Optional[float] = 5.0,
    ):
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.max_connections == other.max_connections
            and self.max_keepalive_connections == other.max_keepalive_connections
            and self.keepalive_expiry == other.keepalive_expiry
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return (
            f"{class_name}(max_connections={self.max_connections}, "
            f"max_keepalive_connections={self.max_keepalive_connections}, "
            f"keepalive_expiry={self.keepalive_expiry})"
        )


class Proxy:
    def __init__(
        self, url: URLTypes, *, headers: HeaderTypes = None, mode: str = "DEFAULT"
    ):
        url = URL(url)
        headers = Headers(headers)

        if url.scheme not in ("http", "https"):
            raise ValueError(f"Unknown scheme for proxy URL {url!r}")
        if mode not in ("DEFAULT", "FORWARD_ONLY", "TUNNEL_ONLY"):
            raise ValueError(f"Unknown proxy mode {mode!r}")

        if url.username or url.password:
            headers.setdefault(
                "Proxy-Authorization",
                self._build_auth_header(url.username, url.password),
            )
            # Remove userinfo from the URL authority, e.g.:
            # 'username:password@proxy_host:proxy_port' -> 'proxy_host:proxy_port'
            url = url.copy_with(username=None, password=None)

        self.url = url
        self.headers = headers
        self.mode = mode

    def _build_auth_header(self, username: str, password: str) -> str:
        userpass = (username.encode("utf-8"), password.encode("utf-8"))
        token = b64encode(b":".join(userpass)).decode()
        return f"Basic {token}"

    def __repr__(self) -> str:
        return (
            f"Proxy(url={str(self.url)!r}, "
            f"headers={dict(self.headers)!r}, "
            f"mode={self.mode!r})"
        )


DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)
DEFAULT_MAX_REDIRECTS = 20
