import ssl
import subprocess
import sys
import typing
from pathlib import Path

import certifi
import pytest

import httpx


def test_load_ssl_config():
    context = httpx.SSLContext()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_non_existing_file():
    with pytest.raises(IOError):
        context = httpx.SSLContext()
        context.load_verify_locations(cafile="/path/to/nowhere")


def test_load_ssl_with_keylog(monkeypatch: typing.Any) -> None:
    monkeypatch.setenv("SSLKEYLOGFILE", "test")
    context = httpx.SSLContext()
    assert context.keylog_filename == "test"


def test_load_ssl_config_verify_existing_file():
    context = httpx.SSLContext()
    context.load_verify_locations(capath=certifi.where())
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_directory():
    context = httpx.SSLContext()
    context.load_verify_locations(capath=Path(certifi.where()).parent)
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key(cert_pem_file, cert_private_key_file):
    context = httpx.SSLContext()
    context.load_cert_chain(cert_pem_file, cert_private_key_file)
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("password", [b"password", "password"])
def test_load_ssl_config_cert_and_encrypted_key(
    cert_pem_file, cert_encrypted_private_key_file, password
):
    context = httpx.SSLContext()
    context.load_cert_chain(cert_pem_file, cert_encrypted_private_key_file, password)
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key_invalid_password(
    cert_pem_file, cert_encrypted_private_key_file
):
    with pytest.raises(ssl.SSLError):
        context = httpx.SSLContext()
        context.load_cert_chain(
            cert_pem_file, cert_encrypted_private_key_file, "password1"
        )


def test_load_ssl_config_cert_without_key_raises(cert_pem_file):
    with pytest.raises(ssl.SSLError):
        context = httpx.SSLContext()
        context.load_cert_chain(cert_pem_file)


def test_load_ssl_config_no_verify():
    context = httpx.SSLContext(verify=False)
    assert context.verify_mode == ssl.VerifyMode.CERT_NONE
    assert context.check_hostname is False


def test_SSLContext_with_get_request(server, cert_pem_file):
    context = httpx.SSLContext()
    context.load_verify_locations(cert_pem_file)
    response = httpx.get(server.url, ssl_context=context)
    assert response.status_code == 200


def test_SSLContext_repr():
    ssl_context = httpx.SSLContext()

    assert repr(ssl_context) == "<SSLContext(verify=True)>"


def test_limits_repr():
    limits = httpx.Limits(max_connections=100)
    expected = (
        "Limits(max_connections=100, max_keepalive_connections=None,"
        " keepalive_expiry=5.0)"
    )
    assert repr(limits) == expected


def test_limits_eq():
    limits = httpx.Limits(max_connections=100)
    assert limits == httpx.Limits(max_connections=100)


def test_timeout_eq():
    timeout = httpx.Timeout(timeout=5.0)
    assert timeout == httpx.Timeout(timeout=5.0)


def test_timeout_all_parameters_set():
    timeout = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
    assert timeout == httpx.Timeout(timeout=5.0)


def test_timeout_from_nothing():
    timeout = httpx.Timeout(None)
    assert timeout.connect is None
    assert timeout.read is None
    assert timeout.write is None
    assert timeout.pool is None


def test_timeout_from_none():
    timeout = httpx.Timeout(timeout=None)
    assert timeout == httpx.Timeout(None)


def test_timeout_from_one_none_value():
    timeout = httpx.Timeout(None, read=None)
    assert timeout == httpx.Timeout(None)


def test_timeout_from_one_value():
    timeout = httpx.Timeout(None, read=5.0)
    assert timeout == httpx.Timeout(timeout=(None, 5.0, None, None))


def test_timeout_from_one_value_and_default():
    timeout = httpx.Timeout(5.0, pool=60.0)
    assert timeout == httpx.Timeout(timeout=(5.0, 5.0, 5.0, 60.0))


def test_timeout_missing_default():
    with pytest.raises(ValueError):
        httpx.Timeout(pool=60.0)


def test_timeout_from_tuple():
    timeout = httpx.Timeout(timeout=(5.0, 5.0, 5.0, 5.0))
    assert timeout == httpx.Timeout(timeout=5.0)


def test_timeout_from_config_instance():
    timeout = httpx.Timeout(timeout=5.0)
    assert httpx.Timeout(timeout) == httpx.Timeout(timeout=5.0)


def test_timeout_repr():
    timeout = httpx.Timeout(timeout=5.0)
    assert repr(timeout) == "Timeout(timeout=5.0)"

    timeout = httpx.Timeout(None, read=5.0)
    assert repr(timeout) == "Timeout(connect=None, read=5.0, write=None, pool=None)"


def test_proxy_from_url():
    proxy = httpx.Proxy("https://example.com")

    assert str(proxy.url) == "https://example.com"
    assert proxy.auth is None
    assert proxy.headers == {}
    assert repr(proxy) == "Proxy('https://example.com')"


def test_proxy_with_auth_from_url():
    proxy = httpx.Proxy("https://username:password@example.com")

    assert str(proxy.url) == "https://example.com"
    assert proxy.auth == ("username", "password")
    assert proxy.headers == {}
    assert repr(proxy) == "Proxy('https://example.com', auth=('username', '********'))"


def test_invalid_proxy_scheme():
    with pytest.raises(ValueError):
        httpx.Proxy("invalid://example.com")


def test_certifi_lazy_loading():
    subprocess.check_call(
        [
            sys.executable,
            "-c",
            "import httpx,sys;assert 'certifi' not in sys.modules;"
            + "_context = httpx.SSLContext();"
            + "assert 'certifi' in sys.modules",
        ]
    )


# ignore warning about unclosed socket which is
# thrown by a failed ssl connection
@pytest.mark.filterwarnings("ignore:unclosed")
def test_can_request_http_without_ssl(
    server,
):
    # make the SSLContext object not derive from ssl
    # as it would if ssl wasn't available
    try:
        old_sslcontext_class = httpx.SSLContext

        class _DummySSLContext:
            def __init__(
                self,
                verify: bool = True,
            ) -> None:
                self.verify = verify

        httpx._config.SSLContext = _DummySSLContext  # type: ignore
        httpx.SSLContext = _DummySSLContext  # type: ignore

        # At this point, http get should still succeed
        response = httpx.get(str(server.url))
        assert response.status_code == 200
        assert response.reason_phrase == "OK"
        assert response.text == "Hello, world!"
        assert response.http_version == "HTTP/1.1"

        # check the SSLContext isn't a valid context
        context = httpx.SSLContext()
        assert not hasattr(context, "verify_mode")

        # https get should raise errors
        with pytest.raises(AttributeError):
            _response = httpx.get("https://example.org", ssl_context=context)
    finally:
        # fix the SSLContext to be back to normal
        httpx.SSLContext = httpx._config.SSLContext = old_sslcontext_class  # type: ignore
