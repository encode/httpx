import os
import ssl
import typing
from pathlib import Path

import certifi

from .__version__ import __version__

CertTypes = typing.Union[str, typing.Tuple[str, str], typing.Tuple[str, str, str]]
VerifyTypes = typing.Union[str, bool, ssl.SSLContext]
TimeoutTypes = typing.Union[float, typing.Tuple[float, float, float], "TimeoutConfig"]
HTTPVersionTypes = typing.Union[
    str, typing.List[str], typing.Tuple[str], "HTTPVersionConfig"
]


USER_AGENT = f"python-httpx/{__version__}"

HTTP_VERSIONS_TO_ALPN_IDENTIFIERS = {"HTTP/1.1": "http/1.1", "HTTP/2": "h2"}

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


class SSLConfig:
    """
    SSL Configuration.
    """

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

    def load_ssl_context(
        self, http_versions: "HTTPVersionConfig" = None
    ) -> ssl.SSLContext:
        http_versions = HTTPVersionConfig() if http_versions is None else http_versions

        if self.ssl_context is None:
            self.ssl_context = (
                self.load_ssl_context_verify(http_versions=http_versions)
                if self.verify
                else self.load_ssl_context_no_verify(http_versions=http_versions)
            )

        assert self.ssl_context is not None
        return self.ssl_context

    def load_ssl_context_no_verify(
        self, http_versions: "HTTPVersionConfig"
    ) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        context = self._create_default_ssl_context(http_versions=http_versions)
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
        return context

    def load_ssl_context_verify(
        self, http_versions: "HTTPVersionConfig"
    ) -> ssl.SSLContext:
        """
        Return an SSL context for verified connections.
        """
        if isinstance(self.verify, bool):
            ca_bundle_path = DEFAULT_CA_BUNDLE_PATH
        elif Path(self.verify).exists():
            ca_bundle_path = Path(self.verify)
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(self.verify)
            )

        context = self._create_default_ssl_context(http_versions=http_versions)
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
            context.load_verify_locations(cafile=str(ca_bundle_path))
        elif ca_bundle_path.is_dir():
            context.load_verify_locations(capath=str(ca_bundle_path))

        self._load_client_certs(context)

        return context

    def _create_default_ssl_context(
        self, http_versions: "HTTPVersionConfig"
    ) -> ssl.SSLContext:
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
            context.set_alpn_protocols(http_versions.alpn_identifiers)

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


class TimeoutConfig:
    """
    Timeout values.
    """

    def __init__(
        self,
        timeout: TimeoutTypes = None,
        *,
        connect_timeout: float = None,
        read_timeout: float = None,
        write_timeout: float = None,
    ):
        if timeout is None:
            self.connect_timeout = connect_timeout
            self.read_timeout = read_timeout
            self.write_timeout = write_timeout
        else:
            # Specified as a single timeout value
            assert connect_timeout is None
            assert read_timeout is None
            assert write_timeout is None
            if isinstance(timeout, TimeoutConfig):
                self.connect_timeout = timeout.connect_timeout
                self.read_timeout = timeout.read_timeout
                self.write_timeout = timeout.write_timeout
            elif isinstance(timeout, tuple):
                self.connect_timeout = timeout[0]
                self.read_timeout = timeout[1]
                self.write_timeout = timeout[2]
            else:
                self.connect_timeout = timeout
                self.read_timeout = timeout
                self.write_timeout = timeout

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.connect_timeout == other.connect_timeout
            and self.read_timeout == other.read_timeout
            and self.write_timeout == other.write_timeout
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if len({self.connect_timeout, self.read_timeout, self.write_timeout}) == 1:
            return f"{class_name}(timeout={self.connect_timeout})"
        return (
            f"{class_name}(connect_timeout={self.connect_timeout}, "
            f"read_timeout={self.read_timeout}, write_timeout={self.write_timeout})"
        )


class HTTPVersionConfig:
    """
    Configure which HTTP protocol versions are supported.
    """

    def __init__(self, http_versions: HTTPVersionTypes = None):
        if http_versions is None:
            http_versions = ["HTTP/1.1", "HTTP/2"]

        if isinstance(http_versions, str):
            self.http_versions = {http_versions.upper()}
        elif isinstance(http_versions, HTTPVersionConfig):
            self.http_versions = http_versions.http_versions
        elif isinstance(http_versions, typing.Iterable):
            self.http_versions = {
                version.upper() if isinstance(version, str) else version
                for version in http_versions
            }
        else:
            raise TypeError(
                f"HTTP version should be a string or list of strings, "
                "but got {type(http_versions)}"
            )

        for version in self.http_versions:
            if version not in ("HTTP/1.1", "HTTP/2"):
                raise ValueError(f"Unsupported HTTP version {version!r}.")

        if not self.http_versions:
            raise ValueError(f"HTTP versions cannot be an empty list.")

    @property
    def alpn_identifiers(self) -> typing.List[str]:
        """
        Returns a list of supported ALPN identifiers. (One or more of "http/1.1", "h2").
        """
        return [
            HTTP_VERSIONS_TO_ALPN_IDENTIFIERS[version] for version in self.http_versions
        ]

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        value = sorted(list(self.http_versions))
        return f"{class_name}({value!r})"


class PoolLimits:
    """
    Limits on the number of connections in a connection pool.
    """

    def __init__(
        self,
        *,
        soft_limit: int = None,
        hard_limit: int = None,
        pool_timeout: float = None,
    ):
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.pool_timeout = pool_timeout

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.soft_limit == other.soft_limit
            and self.hard_limit == other.hard_limit
            and self.pool_timeout == other.pool_timeout
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return (
            f"{class_name}(soft_limit={self.soft_limit}, "
            f"hard_limit={self.hard_limit}, pool_timeout={self.pool_timeout})"
        )


DEFAULT_SSL_CONFIG = SSLConfig(cert=None, verify=True)
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig(timeout=5.0)
DEFAULT_POOL_LIMITS = PoolLimits(soft_limit=10, hard_limit=100, pool_timeout=5.0)
DEFAULT_CA_BUNDLE_PATH = Path(certifi.where())
DEFAULT_MAX_REDIRECTS = 20
