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
        == "TimeoutConfig(connect_timeout=None, read_timeout=5.0, pool_timeout=None)"
    )


def test_limits_repr():
    limits = httpcore.PoolLimits(hard_limit=100)
    assert repr(limits) == "PoolLimits(soft_limit=None, hard_limit=100)"


def test_ssl_eq():
    ssl = httpcore.SSLConfig(verify=False)
    assert ssl == httpcore.SSLConfig(verify=False)


def test_timeout_eq():
    timeout = httpcore.TimeoutConfig(timeout=5.0)
    assert timeout == httpcore.TimeoutConfig(timeout=5.0)


def test_limits_eq():
    limits = httpcore.PoolLimits(hard_limit=100)
    assert limits == httpcore.PoolLimits(hard_limit=100)


def test_ssl_hash():
    cache = {}
    ssl = httpcore.SSLConfig(verify=False)
    cache[ssl] = "example"
    assert cache[httpcore.SSLConfig(verify=False)] == "example"


def test_timeout_hash():
    cache = {}
    timeout = httpcore.TimeoutConfig(timeout=5.0)
    cache[timeout] = "example"
    assert cache[httpcore.TimeoutConfig(timeout=5.0)] == "example"


def test_limits_hash():
    cache = {}
    limits = httpcore.PoolLimits(hard_limit=100)
    cache[limits] = "example"
    assert cache[httpcore.PoolLimits(hard_limit=100)] == "example"
