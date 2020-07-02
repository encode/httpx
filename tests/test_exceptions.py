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

    if not_mapped:
        pytest.fail(f"Unmapped httpcore exceptions: {not_mapped}")


def test_httpcore_exception_mapping() -> None:
    """
    HTTPCore exception mapping works as expected.
    """

    # Make sure we don't just map to `NetworkError`.
    # (TODO: Expose `ConnectError` on `httpx`.)
    with pytest.raises(httpx._exceptions.ConnectError):
        httpx.get("http://doesnotexist")

    # Make sure it also works with custom transports.
    class MockTransport(httpcore.SyncHTTPTransport):
        def request(self, *args: Any, **kwargs: Any) -> Any:
            raise httpcore.ProtocolError()

    client = httpx.Client(transport=MockTransport())
    with pytest.raises(httpx.ProtocolError):
        client.get("http://testserver")
