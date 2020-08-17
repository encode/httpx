from typing import Any

import httpcore
import pytest

import httpx
from httpx._exceptions import HTTPCORE_EXC_MAP


def test_httpcore_all_exceptions_mapped() -> None:
    """
    All exception classes exposed by HTTPCore are properly mapped to an HTTPX-specific
    exception class.
    """
    not_mapped = [
        value
        for name, value in vars(httpcore).items()
        if isinstance(value, type)
        and issubclass(value, Exception)
        and value not in HTTPCORE_EXC_MAP
    ]

    if not_mapped:  # pragma: nocover
        pytest.fail(f"Unmapped httpcore exceptions: {not_mapped}")


def test_httpcore_exception_mapping(server) -> None:
    """
    HTTPCore exception mapping works as expected.
    """

    # Make sure we don't just map to `NetworkError`.
    with pytest.raises(httpx.ConnectError):
        httpx.get("http://doesnotexist")

    # Make sure Response.iter_raw() exceptinos are mapped
    url = server.url.copy_with(path="/slow_stream_response")
    timeout = httpx.Timeout(None, read=0.1)
    with httpx.stream("GET", url, timeout=timeout) as stream:
        with pytest.raises(httpx.ReadTimeout):
            stream.read()

    # Make sure it also works with custom transports.
    class MockTransport(httpcore.SyncHTTPTransport):
        def request(self, *args: Any, **kwargs: Any) -> Any:
            raise httpcore.ProtocolError()

    client = httpx.Client(transport=MockTransport())
    with pytest.raises(httpx.ProtocolError):
        client.get("http://testserver")


def test_httpx_exceptions_exposed() -> None:
    """
    All exception classes defined in `httpx._exceptions`
    are exposed as public API.
    """

    not_exposed = [
        value
        for name, value in vars(httpx._exceptions).items()
        if isinstance(value, type)
        and issubclass(value, Exception)
        and not hasattr(httpx, name)
    ]

    if not_exposed:  # pragma: nocover
        pytest.fail(f"Unexposed HTTPX exceptions: {not_exposed}")
