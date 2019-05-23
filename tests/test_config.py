import os
import ssl

import pytest

import httpcore


@pytest.mark.asyncio
async def test_load_ssl_config():
    ssl_config = httpcore.SSLConfig()
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED


@pytest.mark.asyncio
async def test_load_ssl_config_verify_non_existing_path():
    ssl_config = httpcore.SSLConfig(verify="/path/to/nowhere")
    with pytest.raises(IOError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_verify_existing_file():
    ssl_config = httpcore.SSLConfig(verify=httpcore.config.DEFAULT_CA_BUNDLE_PATH)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED


@pytest.mark.asyncio
async def test_load_ssl_config_verify_directory():
    path = os.path.dirname(httpcore.config.DEFAULT_CA_BUNDLE_PATH)
    ssl_config = httpcore.SSLConfig(verify=path)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED


@pytest.mark.asyncio
async def test_load_ssl_config_cert_and_key(cert_and_key_paths):
    cert_path, key_path = cert_and_key_paths
    ssl_config = httpcore.SSLConfig(cert=(cert_path, key_path))
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED


@pytest.mark.asyncio
async def test_load_ssl_config_cert_without_key_raises(cert_and_key_paths):
    cert_path, _ = cert_and_key_paths
    ssl_config = httpcore.SSLConfig(cert=cert_path)
    with pytest.raises(ssl.SSLError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_no_verify(verify=False):
    ssl_config = httpcore.SSLConfig(verify=False)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE


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


def test_timeout_from_tuple():
    timeout = httpcore.TimeoutConfig(timeout=(5.0, 5.0, 5.0))
    assert timeout == httpcore.TimeoutConfig(timeout=5.0)


def test_timeout_from_config_instance():
    timeout = httpcore.TimeoutConfig(timeout=(5.0))
    assert httpcore.TimeoutConfig(timeout) == httpcore.TimeoutConfig(timeout=5.0)
