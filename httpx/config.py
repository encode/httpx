import os
import ssl
import typing
from pathlib import Path

import certifi

from .__version__ import __version__
from .utils import get_ca_bundle_from_env, get_logger

CertTypes = typing.Union[str, typing.Tuple[str, str], typing.Tuple[str, str, str]]
VerifyTypes = typing.Union[str, bool, ssl.SSLContext]
TimeoutTypes = typing.Union[float, typing.Tuple[float, float, float, float], "Timeout"]


USER_AGENT = f"python-httpx/{__version__}"

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
        trust_env: bool = None,
    ):
        self.cert = cert

        # Allow passing in our own SSLContext object that's pre-configured.
        # If you do this we assume that you want verify=True as well.
        ssl_context = None
        if isinstance(verify, ssl.SSLContext):
            ssl_context = verify
            verify = True
            self._load_client_certs(ssl_context)

        self.ssl_context: typing.Optional[ssl.SSLContext] = ssl_context
        self.verify: typing.Union[str, bool] = verify
        self.trust_env = trust_env

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.cert == other.cert
            and self.verify == other.verify
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(cert={self.cert}, verify={self.verify})"

    def with_overrides(
        self, cert: CertTypes = None, verify: VerifyTypes = None
    ) -> "SSLConfig":
        cert = self.cert if cert is None else cert
        verify = self.verify if verify is None else verify
        if (cert == self.cert) and (verify == self.verify):
            return self
        return SSLConfig(cert=cert, verify=verify)

    def load_ssl_context(self, http2: bool = False) -> ssl.SSLContext:
        logger.trace(
            f"load_ssl_context "
            f"verify={self.verify!r} "
            f"cert={self.cert!r} "
            f"trust_env={self.trust_env!r} "
            f"http2={http2!r}"
        )

        if self.ssl_context is None:
            self.ssl_context = (
                self.load_ssl_context_verify(http2=http2)
                if self.verify
                else self.load_ssl_context_no_verify(http2=http2)
            )

        assert self.ssl_context is not None
        return self.ssl_context

    def load_ssl_context_no_verify(self, http2: bool = False) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        context = self._create_default_ssl_context(http2=http2)
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
        return context

    def load_ssl_context_verify(self, http2: bool = False) -> ssl.SSLContext:
        """
        Return an SSL context for verified connections.
        """
        if self.trust_env and self.verify is True:
            ca_bundle = get_ca_bundle_from_env()
            if ca_bundle is not None:
                self.verify = ca_bundle  # type: ignore

        if isinstance(self.verify, bool):
            ca_bundle_path = self.DEFAULT_CA_BUNDLE_PATH
        elif Path(self.verify).exists():
            ca_bundle_path = Path(self.verify)
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(self.verify)
            )

        context = self._create_default_ssl_context(http2=http2)
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

    def _create_default_ssl_context(self, http2: bool) -> ssl.SSLContext:
        """
        Creates the default SSLContext object that's used for both verified
        and unverified connections.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_NO_COMPRESSION
        context.set_ciphers(DEFAULT_CIPHERS)

        if ssl.HAS_ALPN:
            alpn_idents = ["http/1.1", "h2"] if http2 else ["http/1.1"]
            context.set_alpn_protocols(alpn_idents)

        if hasattr(context, "keylog_filename"):
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

    Timeout()                           # No timeout.
    Timeout(5.0)                        # 5s timeout on all operations.
    Timeout(connect_timeout=5.0)        # 5s timeout on connect, no other timeouts.
    Timeout(5.0, connect_timeout=10.0)  # 10s timeout on connect. 5s timeout elsewhere.
    Timeout(5.0, pool_timeout=None)     # No timeout on acquiring connection from pool.
                                        # 5s timeout elsewhere.
    """

    def __init__(
        self,
        timeout: TimeoutTypes = None,
        *,
        connect_timeout: typing.Union[None, float, UnsetType] = UNSET,
        read_timeout: typing.Union[None, float, UnsetType] = UNSET,
        write_timeout: typing.Union[None, float, UnsetType] = UNSET,
        pool_timeout: typing.Union[None, float, UnsetType] = UNSET,
    ):
        if isinstance(timeout, Timeout):
            # Passed as a single explicit Timeout.
            assert connect_timeout is UNSET
            assert read_timeout is UNSET
            assert write_timeout is UNSET
            assert pool_timeout is UNSET
            self.connect_timeout = (
                timeout.connect_timeout
            )  # type: typing.Optional[float]
            self.read_timeout = timeout.read_timeout  # type: typing.Optional[float]
            self.write_timeout = timeout.write_timeout  # type: typing.Optional[float]
            self.pool_timeout = timeout.pool_timeout  # type: typing.Optional[float]
        elif isinstance(timeout, tuple):
            # Passed as a tuple.
            self.connect_timeout = timeout[0]
            self.read_timeout = timeout[1]
            self.write_timeout = None if len(timeout) < 3 else timeout[2]
            self.pool_timeout = None if len(timeout) < 4 else timeout[3]
        else:
            self.connect_timeout = (
                timeout if isinstance(connect_timeout, UnsetType) else connect_timeout
            )
            self.read_timeout = (
                timeout if isinstance(read_timeout, UnsetType) else read_timeout
            )
            self.write_timeout = (
                timeout if isinstance(write_timeout, UnsetType) else write_timeout
            )
            self.pool_timeout = (
                timeout if isinstance(pool_timeout, UnsetType) else pool_timeout
            )

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.connect_timeout == other.connect_timeout
            and self.read_timeout == other.read_timeout
            and self.write_timeout == other.write_timeout
            and self.pool_timeout == other.pool_timeout
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if (
            len(
                {
                    self.connect_timeout,
                    self.read_timeout,
                    self.write_timeout,
                    self.pool_timeout,
                }
            )
            == 1
        ):
            return f"{class_name}(timeout={self.connect_timeout})"
        return (
            f"{class_name}(connect_timeout={self.connect_timeout}, "
            f"read_timeout={self.read_timeout}, write_timeout={self.write_timeout}, "
            f"pool_timeout={self.pool_timeout})"
        )


class PoolLimits:
    """
    Limits on the number of connections in a connection pool.
    """

    def __init__(
        self, *, soft_limit: int = None, hard_limit: int = None,
    ):
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.soft_limit == other.soft_limit
            and self.hard_limit == other.hard_limit
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return (
            f"{class_name}(soft_limit={self.soft_limit}, hard_limit={self.hard_limit})"
        )


TimeoutConfig = Timeout  # Synonym for backwards compat


DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_POOL_LIMITS = PoolLimits(soft_limit=10, hard_limit=100)
DEFAULT_MAX_REDIRECTS = 20
