import os
import ssl

import pytest

import http3


@pytest.mark.asyncio
async def test_load_ssl_config():
    ssl_config = http3.SSLConfig()
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_verify_non_existing_path():
    ssl_config = http3.SSLConfig(verify="/path/to/nowhere")
    with pytest.raises(IOError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_verify_existing_file():
    ssl_config = http3.SSLConfig(verify=http3.config.DEFAULT_CA_BUNDLE_PATH)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_verify_directory():
    path = os.path.dirname(http3.config.DEFAULT_CA_BUNDLE_PATH)
    ssl_config = http3.SSLConfig(verify=path)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_cert_and_key(cert_and_key_paths):
    cert_path, key_path = cert_and_key_paths
    ssl_config = http3.SSLConfig(cert=(cert_path, key_path))
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_cert_and_key(cert_and_encrypted_key_paths):
    cert_path, key_path = cert_and_encrypted_key_paths
    ssl_config = http3.SSLConfig(cert=(cert_path, key_path, "password"))
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_cert_and_key_invalid_password(
    cert_and_encrypted_key_paths
):
    cert_path, key_path = cert_and_encrypted_key_paths
    ssl_config = http3.SSLConfig(cert=(cert_path, key_path, "password1"))

    with pytest.raises(ssl.SSLError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_cert_without_key_raises(cert_and_key_paths):
    cert_path, _ = cert_and_key_paths
    ssl_config = http3.SSLConfig(cert=cert_path)
    with pytest.raises(ssl.SSLError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_no_verify():
    ssl_config = http3.SSLConfig(verify=False)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE
    assert context.check_hostname is False


def test_ssl_repr():
    ssl = http3.SSLConfig(verify=False)
    assert repr(ssl) == "SSLConfig(cert=None, verify=False)"


def test_timeout_repr():
    timeout = http3.TimeoutConfig(timeout=5.0)
    assert repr(timeout) == "TimeoutConfig(timeout=5.0)"

    timeout = http3.TimeoutConfig(read_timeout=5.0)
    assert (
        repr(timeout)
        == "TimeoutConfig(connect_timeout=None, read_timeout=5.0, write_timeout=None)"
    )


def test_limits_repr():
    limits = http3.PoolLimits(hard_limit=100)
    assert (
        repr(limits) == "PoolLimits(soft_limit=None, hard_limit=100, pool_timeout=None)"
    )


def test_ssl_eq():
    ssl = http3.SSLConfig(verify=False)
    assert ssl == http3.SSLConfig(verify=False)


def test_timeout_eq():
    timeout = http3.TimeoutConfig(timeout=5.0)
    assert timeout == http3.TimeoutConfig(timeout=5.0)


def test_limits_eq():
    limits = http3.PoolLimits(hard_limit=100)
    assert limits == http3.PoolLimits(hard_limit=100)


def test_timeout_from_tuple():
    timeout = http3.TimeoutConfig(timeout=(5.0, 5.0, 5.0))
    assert timeout == http3.TimeoutConfig(timeout=5.0)


def test_timeout_from_config_instance():
    timeout = http3.TimeoutConfig(timeout=5.0)
    assert http3.TimeoutConfig(timeout) == http3.TimeoutConfig(timeout=5.0)
