import os
import socket
import ssl
import sys
from pathlib import Path

import certifi
import pytest

import httpx


def test_load_ssl_config():
    context = httpx.create_ssl_context()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_non_existing_path():
    with pytest.raises(IOError):
        httpx.create_ssl_context(verify="/path/to/nowhere")


def test_load_ssl_config_verify_existing_file():
    context = httpx.create_ssl_context(verify=certifi.where())
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("config", ("SSL_CERT_FILE", "SSL_CERT_DIR"))
def test_load_ssl_config_verify_env_file(https_server, ca_cert_pem_file, config):
    os.environ[config] = (
        ca_cert_pem_file
        if config.endswith("_FILE")
        else str(Path(ca_cert_pem_file).parent)
    )
    context = httpx.create_ssl_context(trust_env=True)

    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True

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
    context = httpx.create_ssl_context(verify=path)
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key(cert_pem_file, cert_private_key_file):
    context = httpx.create_ssl_context(cert=(cert_pem_file, cert_private_key_file))
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("password", [b"password", "password"])
def test_load_ssl_config_cert_and_encrypted_key(
    cert_pem_file, cert_encrypted_private_key_file, password
):
    context = httpx.create_ssl_context(
        cert=(cert_pem_file, cert_encrypted_private_key_file, password)
    )
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key_invalid_password(
    cert_pem_file, cert_encrypted_private_key_file
):
    with pytest.raises(ssl.SSLError):
        httpx.create_ssl_context(
            cert=(cert_pem_file, cert_encrypted_private_key_file, "password1")
        )


def test_load_ssl_config_cert_without_key_raises(cert_pem_file):
    with pytest.raises(ssl.SSLError):
        httpx.create_ssl_context(cert=cert_pem_file)


def test_load_ssl_config_no_verify():
    context = httpx.create_ssl_context(verify=False)
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE
    assert context.check_hostname is False


def test_load_ssl_context():
    ssl_context = ssl.create_default_context()
    context = httpx.create_ssl_context(verify=ssl_context)

    assert context is ssl_context


def test_create_ssl_context_with_get_request(server, cert_pem_file):
    context = httpx.create_ssl_context(verify=cert_pem_file)
    response = httpx.get(server.url, verify=context)
    assert response.status_code == 200


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

        context = httpx.create_ssl_context(trust_env=True)

        assert context.keylog_filename is None

    filename = str(tmpdir.join("test.log"))

    with monkeypatch.context() as m:
        m.setenv("SSLKEYLOGFILE", filename)

        context = httpx.create_ssl_context(trust_env=True)

        assert context.keylog_filename == filename

        context = httpx.create_ssl_context(trust_env=False)

        assert context.keylog_filename is None


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
