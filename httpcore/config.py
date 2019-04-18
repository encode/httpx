import typing

import certifi


class SSLConfig:
    """
    SSL Configuration.
    """

    def __init__(
        self,
        *,
        cert: typing.Union[None, str, typing.Tuple[str, str]] = None,
        verify: typing.Union[str, bool] = True,
    ):
        self.cert = cert
        self.verify = verify

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.cert == other.cert
            and self.verify == other.verify
        )

    def __hash__(self) -> int:
        as_tuple = (self.cert, self.verify)
        return hash(as_tuple)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(cert={self.cert}, verify={self.verify})"


class TimeoutConfig:
    """
    Timeout values.
    """

    def __init__(
        self,
        timeout: float = None,
        *,
        connect_timeout: float = None,
        read_timeout: float = None,
        pool_timeout: float = None,
    ):
        if timeout is not None:
            # Specified as a single timeout value
            assert connect_timeout is None
            assert read_timeout is None
            assert pool_timeout is None
            connect_timeout = timeout
            read_timeout = timeout
            pool_timeout = timeout

        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.pool_timeout = pool_timeout

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.connect_timeout == other.connect_timeout
            and self.read_timeout == other.read_timeout
            and self.pool_timeout == other.pool_timeout
        )

    def __hash__(self) -> int:
        as_tuple = (self.connect_timeout, self.read_timeout, self.pool_timeout)
        return hash(as_tuple)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if self.timeout is not None:
            return f"{class_name}(timeout={self.timeout})"
        return f"{class_name}(connect_timeout={self.connect_timeout}, read_timeout={self.read_timeout}, pool_timeout={self.pool_timeout})"


class PoolLimits:
    """
    Limits on the number of connections in a connection pool.
    """

    def __init__(
        self,
        *,
        soft_limit: typing.Optional[int] = None,
        hard_limit: typing.Optional[int] = None,
    ):
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.soft_limit == other.soft_limit
            and self.hard_limit == other.hard_limit
        )

    def __hash__(self) -> int:
        as_tuple = (self.soft_limit, self.hard_limit)
        return hash(as_tuple)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return (
            f"{class_name}(soft_limit={self.soft_limit}, hard_limit={self.hard_limit})"
        )


DEFAULT_SSL_CONFIG = SSLConfig(cert=None, verify=True)
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig(timeout=5.0)
DEFAULT_POOL_LIMITS = PoolLimits(soft_limit=10, hard_limit=100)
DEFAULT_CA_BUNDLE_PATH = certifi.where()
