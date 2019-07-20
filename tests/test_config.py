import os
import ssl

import httpx
import pytest


@pytest.mark.asyncio
async def test_load_ssl_config():
    ssl_config = httpx.SSLConfig()
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_verify_non_existing_path():
    ssl_config = httpx.SSLConfig(verify="/path/to/nowhere")
    with pytest.raises(IOError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_verify_existing_file():
    ssl_config = httpx.SSLConfig(verify=httpx.config.DEFAULT_CA_BUNDLE_PATH)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_verify_directory():
    path = os.path.dirname(httpx.config.DEFAULT_CA_BUNDLE_PATH)
    ssl_config = httpx.SSLConfig(verify=path)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_cert_and_key(cert_pem_file, cert_private_key_file):
    ssl_config = httpx.SSLConfig(cert=(cert_pem_file, cert_private_key_file))
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
@pytest.mark.parametrize("password", [b"password", "password"])
async def test_load_ssl_config_cert_and_encrypted_key(
    cert_pem_file, cert_encrypted_private_key_file, password
):
    ssl_config = httpx.SSLConfig(
        cert=(cert_pem_file, cert_encrypted_private_key_file, password)
    )
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.asyncio
async def test_load_ssl_config_cert_and_key_invalid_password(
    cert_pem_file, cert_encrypted_private_key_file
):
    ssl_config = httpx.SSLConfig(
        cert=(cert_pem_file, cert_encrypted_private_key_file, "password1")
    )

    with pytest.raises(ssl.SSLError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_cert_without_key_raises(cert_pem_file):
    ssl_config = httpx.SSLConfig(cert=cert_pem_file)
    with pytest.raises(ssl.SSLError):
        await ssl_config.load_ssl_context()


@pytest.mark.asyncio
async def test_load_ssl_config_no_verify():
    ssl_config = httpx.SSLConfig(verify=False)
    context = await ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE
    assert context.check_hostname is False


def test_ssl_repr():
    ssl = httpx.SSLConfig(verify=False)
    assert repr(ssl) == "SSLConfig(cert=None, verify=False)"


def test_timeout_repr():
    timeout = httpx.TimeoutConfig(timeout=5.0)
    assert repr(timeout) == "TimeoutConfig(timeout=5.0)"

    timeout = httpx.TimeoutConfig(read_timeout=5.0)
    assert (
        repr(timeout)
        == "TimeoutConfig(connect_timeout=None, read_timeout=5.0, write_timeout=None)"
    )


def test_limits_repr():
    limits = httpx.PoolLimits(hard_limit=100)
    assert (
        repr(limits) == "PoolLimits(soft_limit=None, hard_limit=100, pool_timeout=None)"
    )


def test_ssl_eq():
    ssl = httpx.SSLConfig(verify=False)
    assert ssl == httpx.SSLConfig(verify=False)


def test_timeout_eq():
    timeout = httpx.TimeoutConfig(timeout=5.0)
    assert timeout == httpx.TimeoutConfig(timeout=5.0)


def test_limits_eq():
    limits = httpx.PoolLimits(hard_limit=100)
    assert limits == httpx.PoolLimits(hard_limit=100)


def test_timeout_from_tuple():
    timeout = httpx.TimeoutConfig(timeout=(5.0, 5.0, 5.0))
    assert timeout == httpx.TimeoutConfig(timeout=5.0)


def test_timeout_from_config_instance():
    timeout = httpx.TimeoutConfig(timeout=5.0)
    assert httpx.TimeoutConfig(timeout) == httpx.TimeoutConfig(timeout=5.0)
