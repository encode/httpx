import asyncio
import email.utils
import enum
import os
import random
import re
import ssl
import time
import typing

import certifi

from .exceptions import HttpError, TooManyRetries
from .models import AsyncRequest, AsyncResponse
from .status_codes import StatusCode

CertTypes = typing.Union[str, typing.Tuple[str, str], typing.Tuple[str, str, str]]
VerifyTypes = typing.Union[str, bool]
TimeoutTypes = typing.Union[float, typing.Tuple[float, float, float], "TimeoutConfig"]
StatusCodeTypes = typing.Union[int, StatusCode]

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

    def __init__(self, *, cert: CertTypes = None, verify: VerifyTypes = True):
        self.cert = cert
        self.verify = verify

        self.ssl_context: typing.Optional[ssl.SSLContext] = None

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

    async def load_ssl_context(self) -> ssl.SSLContext:
        if self.ssl_context is None:
            if not self.verify:
                self.ssl_context = self.load_ssl_context_no_verify()
            else:
                # Run the SSL loading in a threadpool, since it makes disk accesses.
                loop = asyncio.get_event_loop()
                self.ssl_context = await loop.run_in_executor(
                    None, self.load_ssl_context_verify
                )

        assert self.ssl_context is not None
        return self.ssl_context

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
        if isinstance(self.verify, bool):
            ca_bundle_path = DEFAULT_CA_BUNDLE_PATH
        elif os.path.exists(self.verify):
            ca_bundle_path = self.verify
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

        if os.path.isfile(ca_bundle_path):
            context.load_verify_locations(cafile=ca_bundle_path)
        elif os.path.isdir(ca_bundle_path):
            context.load_verify_locations(capath=ca_bundle_path)

        if self.cert is not None:
            if isinstance(self.cert, str):
                context.load_cert_chain(certfile=self.cert)
            elif isinstance(self.cert, tuple) and len(self.cert) == 2:
                context.load_cert_chain(certfile=self.cert[0], keyfile=self.cert[1])
            elif isinstance(self.cert, tuple) and len(self.cert) == 3:
                context.load_cert_chain(
                    certfile=self.cert[0],
                    keyfile=self.cert[1],
                    password=self.cert[2],  # type: ignore
                )

        return context

    def _create_default_ssl_context(self) -> ssl.SSLContext:
        """
        Creates the default SSLContext object that's used for both verified
        and unverified connections.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_COMPRESSION
        context.set_ciphers(DEFAULT_CIPHERS)

        if ssl.HAS_ALPN:
            context.set_alpn_protocols(["h2", "http/1.1"])
        if ssl.HAS_NPN:
            context.set_npn_protocols(["h2", "http/1.1"])

        return context


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


class RetryCause(enum.IntEnum):
    UNKNOWN = 0
    READ = 1
    CONNECT = 2
    RESPONSE = 3
    ERROR = 4


class RetryHistory:
    def __init__(self, cause: RetryCause, request, response=None, error=None):
        self.cause = cause
        self.request = request
        self.response = response
        self.error = error

    def __hash__(self):
        return hash((self.cause, self.request, self.response, self.error))

    def __repr__(self) -> str:
        retry_history = f"RetryHistory(cause={self.cause}, request={self.request}"
        if self.response is not None:
            retry_history += f", response={self.response}"
        if self.error is not None:
            retry_history += f", error={self.error}"
        return retry_history + ")"


class RetryConfig:
    """
    Retry values
    """

    def __init__(
        self,
        total_retries=None,
        *,
        read_retries: int = None,
        connect_retries: int = None,
        retryable_status_codes: typing.Optional[typing.Iterable[StatusCodeTypes]] = (
            413,
            429,
            503,
        ),
        retryable_methods: typing.Optional[typing.Iterable[str]] = (
            "HEAD",
            "GET",
            "PUT",
            "DELETE",
            "OPTIONS",
            "TRACE",
        ),
        retry_after_max: int = 0,
        backoff_factor: float = 0.1,
        backoff_max: float = 10.0,
        backoff_jitter: float = 0.0,
        history: typing.Tuple[RetryHistory, ...] = (),
    ):
        self.total_retries = total_retries
        self.read_retries = read_retries
        self.connect_retries = connect_retries

        self.retryable_methods = retryable_methods
        self.retryable_status_codes = retryable_status_codes

        self.retry_after_max = retry_after_max

        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
        self.backoff_jitter = backoff_jitter

        self.history = history

    def should_retry(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> typing.Optional[AsyncRequest]:

        """Method to be re-implemented by users in case they'd like to modify the request
        that'll be used on the """

        if request.method not in self.retryable_methods:
            return None
        elif response.status_code not in self.retryable_status_codes:
            return None

        return request

    def increment(
        self,
        cause: RetryCause,
        request: AsyncRequest,
        response: typing.Optional[AsyncResponse] = None,
        error: typing.Optional[Exception] = None,
    ) -> "RetryConfig":
        if cause == RetryCause.READ and self.read_retries is not None:
            self.read_retries -= 1
        elif cause == RetryCause.CONNECT and self.connect_retries is not None:
            self.connect_retries -= 1
        if self.total_retries is not None:
            self.total_retries -= 1

        history_entry = RetryHistory(
            cause=cause, request=request, response=response, error=error
        )
        new_history = (history_entry,) + self.history
        if self.is_exhausted():
            raise TooManyRetries(history=new_history)

        return RetryConfig(
            total_retries=self.total_retries,
            read_retries=self.read_retries,
            connect_retries=self.connect_retries,
            retryable_methods=self.retryable_methods,
            retryable_status_codes=self.retryable_status_codes,
            retry_after_max=self.retry_after_max,
            backoff_factor=self.backoff_factor,
            backoff_max=self.backoff_max,
            backoff_jitter=self.backoff_jitter,
            history=new_history,
        )

    def sleep_for_retry(self, response: AsyncResponse) -> float:
        number_of_retries = 0
        backoff = max(
            min(self.backoff_max, self.backoff_factor * (2 ** (number_of_retries - 1))),
            0.0,
        )

        if self.backoff_jitter:
            backoff *= 1.0 - (random.SystemRandom().random() * self.backoff_jitter)

        return backoff + self.get_retry_after(response)

    def get_retry_after(self, response: AsyncResponse) -> int:
        retry_after_header = response.headers.get(b"retry-after", None)
        seconds = 0
        if retry_after_header is not None:
            if re.match(r"^\s*[0-9]+\s*$", retry_after_header):
                seconds = int(retry_after_header.strip())
            else:
                retry_after_date = email.utils.parsedate(retry_after_header)
                if retry_after_date is None:
                    raise HttpError(
                        f"'Retry-After' header is invalid: {retry_after_header}"
                    )
                seconds = int(time.time() - time.mktime(retry_after_date))

        return max(min(int(self.retry_after_max), seconds), 0)

    def is_exhausted(self) -> bool:
        retries = [
            x
            for x in (self.read_retries, self.connect_retries, self.total_retries)
            if x is not None
        ]
        return min(retries) < 0

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, RetryConfig)
            and self.total_retries == other.total_retries
            and self.read_retries == other.read_retries
            and self.connect_retries == other.connect_retries
            and self.retryable_methods == other.retryable_methods
            and self.retryable_status_codes == other.retryable_status_codes
            and self.retry_after_max == other.retry_after_max
            and self.backoff_factor == other.backoff_factor
            and self.backoff_max == other.backoff_max
            and self.backoff_jitter == other.backoff_jitter
        )

    def __hash__(self):
        return hash(
            (
                self.total_retries,
                self.read_retries,
                self.connect_retries,
                self.retryable_methods,
                self.retryable_status_codes,
                self.retry_after_max,
                self.backoff_factor,
                self.backoff_max,
                self.backoff_jitter,
            )
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return (
            f"{class_name}(read_retries={self.read_retries}, "
            f"write_retries={self.write_retries}, "
            f"connect_retries={self.connect_retries})"
        )


DEFAULT_SSL_CONFIG = SSLConfig(cert=None, verify=True)
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig(timeout=5.0)
DEFAULT_POOL_LIMITS = PoolLimits(soft_limit=10, hard_limit=100, pool_timeout=5.0)
DEFAULT_RETRY_CONFIG = RetryConfig(5)
DEFAULT_CA_BUNDLE_PATH = certifi.where()
DEFAULT_MAX_REDIRECTS = 20
