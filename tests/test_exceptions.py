from unittest import mock

import httpcore
import pytest

import httpx
from httpx._transports.default import HTTPCORE_EXC_MAP


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
        and value is not httpcore.ConnectionNotAvailable
    ]

    if not_mapped:  # pragma: no cover
        pytest.fail(f"Unmapped httpcore exceptions: {not_mapped}")


def test_httpcore_exception_mapping(server) -> None:
    """
    HTTPCore exception mapping works as expected.
    """

    def connect_failed(*args, **kwargs):
        raise httpcore.ConnectError()

    class TimeoutStream:
        def __iter__(self):
            raise httpcore.ReadTimeout()

        def close(self):
            pass

    with mock.patch(
        "httpcore.ConnectionPool.handle_request", side_effect=connect_failed
    ):
        with pytest.raises(httpx.ConnectError):
            httpx.get(server.url)

    with mock.patch(
        "httpcore.ConnectionPool.handle_request",
        return_value=httpcore.Response(
            200, headers=[], content=TimeoutStream(), extensions={}
        ),
    ):
        with pytest.raises(httpx.ReadTimeout):
            httpx.get(server.url)


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

    if not_exposed:  # pragma: no cover
        pytest.fail(f"Unexposed HTTPX exceptions: {not_exposed}")


def test_request_attribute() -> None:
    # Exception without request attribute
    exc = httpx.ReadTimeout("Read operation timed out")
    with pytest.raises(RuntimeError):
        exc.request

    # Exception with request attribute
    request = httpx.Request("GET", "https://www.example.com")
    exc = httpx.ReadTimeout("Read operation timed out", request=request)
    assert exc.request == request
