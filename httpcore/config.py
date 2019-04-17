import typing

import certifi


class SSLConfig:
    """
    SSL Configuration.
    """

    def __init__(self, *, cert: typing.Optional[str], verify: typing.Union[str, bool]):
        self.cert = cert
        self.verify = verify


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
        pool_timeout: float = None
    ):
        if timeout is not None:
            # Specified as a single timeout value
            assert connect_timeout is None
            assert read_timeout is None
            assert pool_timeout is None
            connect_timeout = timeout
            read_timeout = timeout
            pool_timeout = timeout

        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.pool_timeout = pool_timeout


class PoolLimits:
    """
    Limits on the number of connections in a connection pool.
    """

    def __init__(
        self,
        *,
        soft_limit: typing.Optional[int] = None,
        hard_limit: typing.Optional[int] = None
    ):
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit


DEFAULT_SSL_CONFIG = SSLConfig(cert=None, verify=True)
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig(timeout=5.0)
DEFAULT_POOL_LIMITS = PoolLimits(soft_limit=10, hard_limit=100)
DEFAULT_CA_BUNDLE_PATH = certifi.where()
