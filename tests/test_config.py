import httpcore


def test_ssl_repr():
    ssl = httpcore.SSLConfig(verify=False)
    assert repr(ssl) == "SSLConfig(cert=None, verify=False)"


def test_timeout_repr():
    timeout = httpcore.TimeoutConfig(timeout=5.0)
    assert repr(timeout) == "TimeoutConfig(timeout=5.0)"

    timeout = httpcore.TimeoutConfig(read_timeout=5.0)
    assert (
        repr(timeout)
        == "TimeoutConfig(connect_timeout=None, read_timeout=5.0, write_timeout=None)"
    )


def test_limits_repr():
    limits = httpcore.PoolLimits(hard_limit=100)
    assert (
        repr(limits) == "PoolLimits(soft_limit=None, hard_limit=100, pool_timeout=None)"
    )


def test_ssl_eq():
    ssl = httpcore.SSLConfig(verify=False)
    assert ssl == httpcore.SSLConfig(verify=False)


def test_timeout_eq():
    timeout = httpcore.TimeoutConfig(timeout=5.0)
    assert timeout == httpcore.TimeoutConfig(timeout=5.0)


def test_limits_eq():
    limits = httpcore.PoolLimits(hard_limit=100)
    assert limits == httpcore.PoolLimits(hard_limit=100)
