import os
import socket
import ssl
import sys
from pathlib import Path

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


@pytest.mark.parametrize("config", ("SSL_CERT_FILE", "SSL_CERT_DIR"))
def test_load_ssl_config_verify_env_file(https_server, ca_cert_pem_file, config):
    os.environ[config] = (
        ca_cert_pem_file
        if config.endswith("_FILE")
        else str(Path(ca_cert_pem_file).parent)
    )
    ssl_config = httpx.SSLConfig(trust_env=True)
    context = ssl_config.load_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True
    assert ssl_config.verify == os.environ[config]

    # Skipping 'SSL_CERT_DIR' functional test for now because
    # we're unable to get the certificate within the directory to
    # load into the SSLContext. :(
    if config == "SSL_CERT_FILE":
        host = https_server.url.host
        port = https_server.url.port
        conn = socket.create_connection((host, port))
        context.wrap_socket(conn, server_hostname=host)
        assert len(context.get_ca_certs()) == 1


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


def test_limits_repr():
    limits = httpx.PoolLimits(hard_limit=100)
    assert repr(limits) == "PoolLimits(soft_limit=None, hard_limit=100)"


def test_ssl_eq():
    ssl = httpx.SSLConfig(verify=False)
    assert ssl == httpx.SSLConfig(verify=False)


def test_limits_eq():
    limits = httpx.PoolLimits(hard_limit=100)
    assert limits == httpx.PoolLimits(hard_limit=100)


def test_timeout_eq():
    timeout = httpx.TimeoutConfig(timeout=5.0)
    assert timeout == httpx.TimeoutConfig(timeout=5.0)


def test_timeout_from_nothing():
    timeout = httpx.TimeoutConfig()
    assert timeout.connect_timeout is None
    assert timeout.read_timeout is None
    assert timeout.write_timeout is None
    assert timeout.pool_timeout is None


def test_timeout_from_none():
    timeout = httpx.TimeoutConfig(timeout=None)
    assert timeout == httpx.TimeoutConfig()


def test_timeout_from_one_none_value():
    timeout = httpx.TimeoutConfig(read_timeout=None)
    assert timeout == httpx.TimeoutConfig()


def test_timeout_from_tuple():
    timeout = httpx.TimeoutConfig(timeout=(5.0, 5.0, 5.0, 5.0))
    assert timeout == httpx.TimeoutConfig(timeout=5.0)


def test_timeout_from_config_instance():
    timeout = httpx.TimeoutConfig(timeout=5.0)
    assert httpx.TimeoutConfig(timeout) == httpx.TimeoutConfig(timeout=5.0)


def test_timeout_repr():
    timeout = httpx.TimeoutConfig(timeout=5.0)
    assert repr(timeout) == "TimeoutConfig(timeout=5.0)"

    timeout = httpx.TimeoutConfig(read_timeout=5.0)
    assert repr(timeout) == (
        "TimeoutConfig(connect_timeout=None, read_timeout=5.0, "
        "write_timeout=None, pool_timeout=None)"
    )


@pytest.mark.skipif(
    not hasattr(ssl.SSLContext, "keylog_filename"),
    reason="requires OpenSSL 1.1.1 or higher",
)
@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
def test_ssl_config_support_for_keylog_file(tmpdir, monkeypatch):
    with monkeypatch.context() as m:
        m.delenv("SSLKEYLOGFILE", raising=False)

        ssl_config = httpx.SSLConfig(trust_env=True)
        ssl_config.load_ssl_context()

        assert ssl_config.ssl_context.keylog_filename is None

    filename = str(tmpdir.join("test.log"))

    with monkeypatch.context() as m:
        m.setenv("SSLKEYLOGFILE", filename)

        ssl_config = httpx.SSLConfig(trust_env=True)
        ssl_config.load_ssl_context()

        assert ssl_config.ssl_context.keylog_filename == filename

        ssl_config = httpx.SSLConfig(trust_env=False)
        ssl_config.load_ssl_context()

        assert ssl_config.ssl_context.keylog_filename is None
