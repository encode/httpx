import os
import ssl
import sys

import pytest

import httpx


def test_load_ssl_config():
    ssl_config = httpx.SSLConfig()
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_non_existing_path():
    ssl_config = httpx.SSLConfig(verify="/path/to/nowhere")
    with pytest.raises(IOError):
        ssl_config.load_ssl_context()


def test_load_ssl_config_verify_existing_file():
    ssl_config = httpx.SSLConfig(verify=httpx.config.DEFAULT_CA_BUNDLE_PATH)
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_directory():
    path = httpx.config.DEFAULT_CA_BUNDLE_PATH.parent
    ssl_config = httpx.SSLConfig(verify=path)
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key(cert_pem_file, cert_private_key_file):
    ssl_config = httpx.SSLConfig(cert=(cert_pem_file, cert_private_key_file))
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("password", [b"password", "password"])
def test_load_ssl_config_cert_and_encrypted_key(
    cert_pem_file, cert_encrypted_private_key_file, password
):
    ssl_config = httpx.SSLConfig(
        cert=(cert_pem_file, cert_encrypted_private_key_file, password)
    )
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key_invalid_password(
    cert_pem_file, cert_encrypted_private_key_file
):
    ssl_config = httpx.SSLConfig(
        cert=(cert_pem_file, cert_encrypted_private_key_file, "password1")
    )

    with pytest.raises(ssl.SSLError):
        ssl_config.load_ssl_context()


def test_load_ssl_config_cert_without_key_raises(cert_pem_file):
    ssl_config = httpx.SSLConfig(cert=cert_pem_file)
    with pytest.raises(ssl.SSLError):
        ssl_config.load_ssl_context()


def test_load_ssl_config_no_verify():
    ssl_config = httpx.SSLConfig(verify=False)
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE
    assert context.check_hostname is False


def test_load_ssl_context():
    ssl_context = ssl.create_default_context()
    ssl_config = httpx.SSLConfig(verify=ssl_context)

    assert ssl_config.verify is True
    assert ssl_config.ssl_context is ssl_context
    assert repr(ssl_config) == "SSLConfig(cert=None, verify=True)"


def test_ssl_repr():
    ssl = httpx.SSLConfig(verify=False)
    assert repr(ssl) == "SSLConfig(cert=None, verify=False)"


def test_http_versions_repr():
    http_versions = httpx.HTTPVersionConfig()
    assert repr(http_versions) == "HTTPVersionConfig(['HTTP/1.1', 'HTTP/2'])"


def test_http_versions_from_string():
    http_versions = httpx.HTTPVersionConfig("HTTP/1.1")
    assert repr(http_versions) == "HTTPVersionConfig(['HTTP/1.1'])"


def test_http_versions_from_list():
    http_versions = httpx.HTTPVersionConfig(["http/1.1"])
    assert repr(http_versions) == "HTTPVersionConfig(['HTTP/1.1'])"


def test_http_versions_from_config():
    http_versions = httpx.HTTPVersionConfig(httpx.HTTPVersionConfig("HTTP/1.1"))
    assert repr(http_versions) == "HTTPVersionConfig(['HTTP/1.1'])"


def test_invalid_http_version():
    with pytest.raises(ValueError):
        httpx.HTTPVersionConfig("HTTP/9")


def test_invalid_http_version_type():
    with pytest.raises(TypeError):
        httpx.HTTPVersionConfig(123)


def test_invalid_http_version_list_type():
    with pytest.raises(ValueError):
        httpx.HTTPVersionConfig([123])


def test_empty_http_version():
    with pytest.raises(ValueError):
        httpx.HTTPVersionConfig([])


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


@pytest.mark.skipif(
    not hasattr(ssl.SSLContext, "keylog_filename"),
    reason="requires OpenSSL 1.1.1 or higher",
)
@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
def test_ssl_config_support_for_keylog_file(tmpdir):
    old = os.getenv("SSLKEYLOGFILE")
    if old is not None:
        del os.environ["SSLKEYLOGFILE"]

    ssl_config = httpx.SSLConfig()
    ssl_config.load_ssl_context()

    assert ssl_config.ssl_context.keylog_filename is None

    filename = str(tmpdir.join("test.log"))
    os.environ["SSLKEYLOGFILE"] = filename

    ssl_config = httpx.SSLConfig()
    ssl_config.load_ssl_context()

    assert ssl_config.ssl_context.keylog_filename == filename

    if old is None:
        del os.environ["SSLKEYLOGFILE"]
    else:
        os.environ["SSLKEYLOGFILE"] = old
