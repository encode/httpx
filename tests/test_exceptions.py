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
    ]

    if not_mapped:  # pragma: nocover
        pytest.fail(f"Unmapped httpcore exceptions: {not_mapped}")


def test_httpcore_exception_mapping(server) -> None:
    """
    HTTPCore exception mapping works as expected.
    """

    def connect_failed(*args, **kwargs):
        raise httpx.ConnectError("connect error")

    class TimeoutStream(httpx._core.ByteStream):
        def __iter__(self):
            raise httpx.ReadTimeout("read timeout")

        def close(self):
            pass

    class CloseFailedStream(httpx._core.ByteStream):
        def __iter__(self):
            yield b""

        def close(self):
            raise httpx.CloseError("close error")

    with mock.patch(
        "httpx._core._sync.connection_pool.ConnectionPool.handle_request",
        side_effect=connect_failed,
    ):
        with pytest.raises(httpx.ConnectError):
            httpx.get(server.url)

    with mock.patch(
        "httpx._core._sync.connection_pool.ConnectionPool.handle_request",
        return_value=httpx._core.RawResponse(200, [], TimeoutStream()),
    ):
        with pytest.raises(httpx.ReadTimeout):
            httpx.get(server.url)

    with mock.patch(
        "httpx._core._sync.connection_pool.ConnectionPool.handle_request",
        return_value=httpx._core.RawResponse(200, [], CloseFailedStream()),
    ):
        with pytest.raises(httpx.CloseError):
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

    if not_exposed:  # pragma: nocover
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
