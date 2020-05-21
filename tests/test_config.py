import os
import socket
import ssl
import sys
from pathlib import Path

import certifi
import pytest

import httpx
from httpx._config import SSLConfig


def test_load_ssl_config():
    ssl_config = SSLConfig()
    context = ssl_config.ssl_context
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_non_existing_path():
    with pytest.raises(IOError):
        SSLConfig(verify="/path/to/nowhere")


def test_load_ssl_config_verify_existing_file():
    ssl_config = SSLConfig(verify=certifi.where())
    context = ssl_config.ssl_context
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("config", ("SSL_CERT_FILE", "SSL_CERT_DIR"))
def test_load_ssl_config_verify_env_file(https_server, ca_cert_pem_file, config):
    os.environ[config] = (
        ca_cert_pem_file
        if config.endswith("_FILE")
        else str(Path(ca_cert_pem_file).parent)
    )
    ssl_config = SSLConfig(trust_env=True)
    context = ssl_config.ssl_context
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
    path = Path(certifi.where()).parent
    ssl_config = SSLConfig(verify=path)
    context = ssl_config.ssl_context
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key(cert_pem_file, cert_private_key_file):
    ssl_config = SSLConfig(cert=(cert_pem_file, cert_private_key_file))
    context = ssl_config.ssl_context
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("password", [b"password", "password"])
def test_load_ssl_config_cert_and_encrypted_key(
    cert_pem_file, cert_encrypted_private_key_file, password
):
    ssl_config = SSLConfig(
        cert=(cert_pem_file, cert_encrypted_private_key_file, password)
    )
    context = ssl_config.ssl_context
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key_invalid_password(
    cert_pem_file, cert_encrypted_private_key_file
):
    with pytest.raises(ssl.SSLError):
        SSLConfig(cert=(cert_pem_file, cert_encrypted_private_key_file, "password1"))


def test_load_ssl_config_cert_without_key_raises(cert_pem_file):
    with pytest.raises(ssl.SSLError):
        SSLConfig(cert=cert_pem_file)


def test_load_ssl_config_no_verify():
    ssl_config = SSLConfig(verify=False)
    context = ssl_config.ssl_context
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE
    assert context.check_hostname is False


def test_load_ssl_context():
    ssl_context = ssl.create_default_context()
    ssl_config = SSLConfig(verify=ssl_context)

    assert ssl_config.ssl_context is ssl_context


def test_ssl_repr():
    ssl = SSLConfig(verify=False)
    assert repr(ssl) == "SSLConfig(cert=None, verify=False)"


def test_ssl_eq():
    ssl = SSLConfig(verify=False)
    assert ssl == SSLConfig(verify=False)


def test_limits_repr():
    limits = httpx.PoolLimits(max_connections=100)
    assert repr(limits) == "PoolLimits(max_keepalive=None, max_connections=100)"


def test_limits_eq():
    limits = httpx.PoolLimits(max_connections=100)
    assert limits == httpx.PoolLimits(max_connections=100)


def test_timeout_eq():
    timeout = httpx.Timeout(timeout=5.0)
    assert timeout == httpx.Timeout(timeout=5.0)


def test_timeout_from_nothing():
    timeout = httpx.Timeout()
    assert timeout.connect_timeout is None
    assert timeout.read_timeout is None
    assert timeout.write_timeout is None
    assert timeout.pool_timeout is None


def test_timeout_from_none():
    timeout = httpx.Timeout(timeout=None)
    assert timeout == httpx.Timeout()


def test_timeout_from_one_none_value():
    timeout = httpx.Timeout(read_timeout=None)
    assert timeout == httpx.Timeout()


def test_timeout_from_one_value():
    timeout = httpx.Timeout(read_timeout=5.0)
    assert timeout == httpx.Timeout(timeout=(None, 5.0, None, None))


def test_timeout_from_one_value_and_default():
    timeout = httpx.Timeout(5.0, pool_timeout=60.0)
    assert timeout == httpx.Timeout(timeout=(5.0, 5.0, 5.0, 60.0))


def test_timeout_from_tuple():
    timeout = httpx.Timeout(timeout=(5.0, 5.0, 5.0, 5.0))
    assert timeout == httpx.Timeout(timeout=5.0)


def test_timeout_from_config_instance():
    timeout = httpx.Timeout(timeout=5.0)
    assert httpx.Timeout(timeout) == httpx.Timeout(timeout=5.0)


def test_timeout_repr():
    timeout = httpx.Timeout(timeout=5.0)
    assert repr(timeout) == "Timeout(timeout=5.0)"

    timeout = httpx.Timeout(read_timeout=5.0)
    assert repr(timeout) == (
        "Timeout(connect_timeout=None, read_timeout=5.0, "
        "write_timeout=None, pool_timeout=None)"
    )


@pytest.mark.skipif(
    not hasattr(ssl.SSLContext, "keylog_filename"),
    reason="requires OpenSSL 1.1.1 or higher",
)
@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
def test_ssl_config_support_for_keylog_file(tmpdir, monkeypatch):  # pragma: nocover
    with monkeypatch.context() as m:
        m.delenv("SSLKEYLOGFILE", raising=False)

        ssl_config = SSLConfig(trust_env=True)

        assert ssl_config.ssl_context.keylog_filename is None

    filename = str(tmpdir.join("test.log"))

    with monkeypatch.context() as m:
        m.setenv("SSLKEYLOGFILE", filename)

        ssl_config = SSLConfig(trust_env=True)

        assert ssl_config.ssl_context.keylog_filename == filename

        ssl_config = SSLConfig(trust_env=False)

        assert ssl_config.ssl_context.keylog_filename is None


@pytest.mark.parametrize(
    "url,expected_url,expected_headers,expected_mode",
    [
        ("https://example.com", "https://example.com", {}, "DEFAULT"),
        (
            "https://user:pass@example.com",
            "https://example.com:443",
            {"proxy-authorization": "Basic dXNlcjpwYXNz"},
            "DEFAULT",
        ),
    ],
)
def test_proxy_from_url(url, expected_url, expected_headers, expected_mode):
    proxy = httpx.Proxy(url)

    assert str(proxy.url) == expected_url
    assert dict(proxy.headers) == expected_headers
    assert proxy.mode == expected_mode
    assert repr(proxy) == "Proxy(url='{}', headers={}, mode='{}')".format(
        expected_url, str(expected_headers), expected_mode
    )


def test_invalid_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.Proxy("invalid://example.com")


def test_invalid_proxy_mode():
    with pytest.raises(ValueError):
        httpx.Proxy("https://example.com", mode="INVALID")
