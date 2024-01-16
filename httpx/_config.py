import logging
import ssl
import typing
from pathlib import Path

import certifi

from ._compat import set_minimum_tls_version_1_2
from ._models import Headers
from ._types import CertTypes, HeaderTypes, TimeoutTypes, URLTypes, VerifyTypes
from ._urls import URL

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


logger = logging.getLogger("httpx")


class UnsetType:
    pass  # pragma: no cover


UNSET = UnsetType()


class SSLContext(ssl.SSLContext):
    DEFAULT_CA_BUNDLE_PATH = Path(certifi.where())

    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: typing.Optional[CertTypes] = None,
    ) -> None:
        self.verify = verify
        set_minimum_tls_version_1_2(self)
        self.options |= ssl.OP_NO_COMPRESSION
        self.set_ciphers(DEFAULT_CIPHERS)

        logger.debug(
            "load_ssl_context verify=%r cert=%r",
            verify,
            cert,
        )

        if verify:
            self.load_ssl_context_verify(cert, verify)
        else:
            self.load_ssl_context_no_verify(cert)

    def load_ssl_context_no_verify(
        self, cert: typing.Optional[CertTypes]
    ) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        self.check_hostname = False
        self.verify_mode = ssl.CERT_NONE
        self._load_client_certs(cert)
        return self

    def load_ssl_context_verify(
        self, cert: typing.Optional[CertTypes], verify: VerifyTypes
    ) -> None:
        """
        Return an SSL context for verified connections.
        """
        if isinstance(verify, bool):
            ca_bundle_path = self.DEFAULT_CA_BUNDLE_PATH
        elif Path(verify).exists():
            ca_bundle_path = Path(verify)
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(verify)
            )

        self.verify_mode = ssl.CERT_REQUIRED
        self.check_hostname = True

        # Signal to server support for PHA in TLS 1.3. Raises an
        # AttributeError if only read-only access is implemented.
        try:
            self.post_handshake_auth = True
        except AttributeError:  # pragma: no cover
            pass

        # Disable using 'commonName' for SSLContext.check_hostname
        # when the 'subjectAltName' extension isn't available.
        try:
            self.hostname_checks_common_name = False
        except AttributeError:  # pragma: no cover
            pass

        if ca_bundle_path.is_file():
            cafile = str(ca_bundle_path)
            logger.debug("load_verify_locations cafile=%r", cafile)
            self.load_verify_locations(cafile=cafile)
        elif ca_bundle_path.is_dir():
            capath = str(ca_bundle_path)
            logger.debug("load_verify_locations capath=%r", capath)
            self.load_verify_locations(capath=capath)

        self._load_client_certs(cert)

    def _load_client_certs(self, cert: typing.Optional[CertTypes] = None) -> None:
        """
        Loads client certificates into our SSLContext object
        """
        if cert is not None:
            if isinstance(cert, str):
                self.load_cert_chain(certfile=cert)
            elif isinstance(cert, tuple) and len(cert) == 2:
                self.load_cert_chain(certfile=cert[0], keyfile=cert[1])
            elif isinstance(cert, tuple) and len(cert) == 3:
                self.load_cert_chain(
                    certfile=cert[0],
                    keyfile=cert[1],
                    password=cert[2],
                )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__

        return f"{class_name}(verify={self.verify!r})"

    def __new__(
        cls,
        protocol: ssl._SSLMethod = ssl.PROTOCOL_TLS_CLIENT,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> "SSLContext":
        return super().__new__(cls, protocol, *args, **kwargs)


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
    ) -> None:
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
    * **keepalive_expiry** - Time limit on idle keep-alive connections in seconds.
    """

    def __init__(
        self,
        *,
        max_connections: typing.Optional[int] = None,
        max_keepalive_connections: typing.Optional[int] = None,
        keepalive_expiry: typing.Optional[float] = 5.0,
    ) -> None:
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
        self,
        url: URLTypes,
        *,
        ssl_context: typing.Optional[ssl.SSLContext] = None,
        auth: typing.Optional[typing.Tuple[str, str]] = None,
        headers: typing.Optional[HeaderTypes] = None,
    ) -> None:
        url = URL(url)
        headers = Headers(headers)

        if url.scheme not in ("http", "https", "socks5"):
            raise ValueError(f"Unknown scheme for proxy URL {url!r}")

        if url.username or url.password:
            # Remove any auth credentials from the URL.
            auth = (url.username, url.password)
            url = url.copy_with(username=None, password=None)

        self.url = url
        self.auth = auth
        self.headers = headers
        self.ssl_context = ssl_context

    @property
    def raw_auth(self) -> typing.Optional[typing.Tuple[bytes, bytes]]:
        # The proxy authentication as raw bytes.
        return (
            None
            if self.auth is None
            else (self.auth[0].encode("utf-8"), self.auth[1].encode("utf-8"))
        )

    def __repr__(self) -> str:
        # The authentication is represented with the password component masked.
        auth = (self.auth[0], "********") if self.auth else None

        # Build a nice concise representation.
        url_str = f"{str(self.url)!r}"
        auth_str = f", auth={auth!r}" if auth else ""
        headers_str = f", headers={dict(self.headers)!r}" if self.headers else ""
        return f"Proxy({url_str}{auth_str}{headers_str})"


DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)
DEFAULT_MAX_REDIRECTS = 20
