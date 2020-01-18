import itertools
import os
import ssl
import typing
from pathlib import Path

import certifi

from .models import URL, Headers, HeaderTypes, Request, Response, URLTypes
from .retries import DontRetry, RetryLimits, RetryOnConnectionFailures
from .utils import get_ca_bundle_from_env, get_logger

CertTypes = typing.Union[str, typing.Tuple[str, str], typing.Tuple[str, str, str]]
VerifyTypes = typing.Union[str, bool, ssl.SSLContext]
TimeoutTypes = typing.Union[
    None, float, typing.Tuple[float, float, float, float], "Timeout"
]
ProxiesTypes = typing.Union[
    URLTypes, "Proxy", typing.Dict[URLTypes, typing.Union[URLTypes, "Proxy"]]
]
RetriesTypes = typing.Union[int, "RetryLimits", "Retries"]


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
        http2: bool = False,
    ):
        self.cert = cert
        self.verify = verify
        self.trust_env = trust_env
        self.http2 = http2
        self.ssl_context = self.load_ssl_context()

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.cert == other.cert
            and self.verify == other.verify
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(cert={self.cert}, verify={self.verify})"

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
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
        return context

    def load_ssl_context_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for verified connections.
        """
        if self.trust_env and self.verify is True:
            ca_bundle = get_ca_bundle_from_env()
            if ca_bundle is not None:
                self.verify = ca_bundle  # type: ignore

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
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
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

    **Parameters:**

    * **soft_limit** - Allow the connection pool to maintain keep-alive connections
                       below this point.
    * **hard_limit** - The maximum number of concurrenct connections that may be
                       established.
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


class Proxy:
    def __init__(
        self, url: URLTypes, *, headers: HeaderTypes = None, mode: str = "DEFAULT",
    ):
        url = URL(url)
        headers = Headers(headers)

        if url.scheme not in ("http", "https"):
            raise ValueError(f"Unknown scheme for proxy URL {url!r}")
        if mode not in ("DEFAULT", "CONNECT_ONLY", "TUNNEL_ONLY"):
            raise ValueError(f"Unknown proxy mode {mode!r}")

        self.url = url
        self.headers = headers
        self.mode = mode

    def __repr__(self) -> str:
        return (
            f"Proxy(url={str(self.url)!r}, "
            f"headers={dict(self.headers)!r}, "
            f"mode={self.mode!r})"
        )


class Retries:
    """
    Retries configuration.

    Holds a retry limiting policy, and implements a configurable exponential
    backoff algorithm.
    """

    def __init__(
        self,
        *retries: RetriesTypes,
        backoff_factor: float = None,
    ) -> None:
        limits: RetriesTypes

        if len(retries) == 0:
            limits = RetryOnConnectionFailures(3)
        elif len(retries) == 1:
            limits = retries[0]
            if isinstance(limits, int):
                limits = (
                    RetryOnConnectionFailures(limits) if limits > 0 else DontRetry()
                )
            elif isinstance(limits, Retries):
                assert backoff_factor is None
                backoff_factor = limits.backoff_factor
                limits = limits.limits
            else:
                raise NotImplementedError(
                    "Passing a `RetryLimits` subclass as a single argument "
                    "is not supported. You must explicitly pass the number of times "
                    "to retry on connection failures. "
                    "For example: `Retries(3, MyRetryLimits(...))`."
                )
        elif len(retries) == 2:
            default, custom = retries
            assert isinstance(custom, RetryLimits)
            limits = Retries(default).limits | custom
        else:
            raise NotImplementedError(
                "Composing more than 2 retry limits is not supported yet."
            )

        if backoff_factor is None:
            backoff_factor = 0.2

        assert backoff_factor > 0
        self.limits: RetryLimits = limits
        self.backoff_factor: float = backoff_factor

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Retries)
            and self.limits == other.limits
            and self.backoff_factor == other.backoff_factor
        )

    def get_delays(self) -> typing.Iterator[float]:
        """
        Used by clients to determine how long to wait before issuing a new request.
        """
        yield 0  # Send the initial request.
        yield 0  # Retry immediately.
        for n in itertools.count(2):
            yield self.backoff_factor * (2 ** (n - 2))

    def retry_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        """
        Used by clients to determine what to do when failing to receive a response,
        or when a response was received.

        Delegates to the retry limiting policy.
        """
        yield from self.limits.retry_flow(request)


DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_RETRIES_CONFIG = Retries(3, backoff_factor=0.2)
DEFAULT_POOL_LIMITS = PoolLimits(soft_limit=10, hard_limit=100)
DEFAULT_MAX_REDIRECTS = 20
