import collections
import itertools
from typing import Dict, List, Mapping, Optional, Tuple

import httpcore
import pytest

import httpx
from httpx._utils import exponential_backoff


def test_retries_config() -> None:
    client = httpx.Client()
    assert client.retries == 0

    client = httpx.Client(retries=3)
    assert client.retries == 3

    client.retries = 1
    assert client.retries == 1


class BaseMockTransport:
    def __init__(self, num_failures: int) -> None:
        self._num_failures = num_failures
        self._attempts_by_path: Dict[bytes, int] = collections.defaultdict(int)

    def _request(
        self,
        url: Tuple[bytes, bytes, Optional[int], bytes],
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.PlainByteStream]:
        _, _, _, path = url

        exc, is_retryable = {
            b"/": (None, False),
            b"/connect_timeout": (httpcore.ConnectTimeout, True),
            b"/connect_error": (httpcore.ConnectError, True),
            b"/read_timeout": (httpcore.ReadTimeout, False),
            b"/network_error": (httpcore.NetworkError, False),
        }[path]

        if exc is None:
            stream = httpcore.PlainByteStream(b"")
            return (b"HTTP/1.1", 200, b"OK", [], stream)

        if not is_retryable:
            raise exc

        if self._attempts_by_path[path] >= self._num_failures:
            self._attempts_by_path.clear()
            stream = httpcore.PlainByteStream(b"")
            return (b"HTTP/1.1", 200, b"OK", [], stream)

        self._attempts_by_path[path] += 1

        raise exc


class MockTransport(BaseMockTransport, httpcore.SyncHTTPTransport):
    def __init__(self, num_failures: int) -> None:
        super().__init__(num_failures)

    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        timeout: Mapping[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.SyncByteStream]:
        return self._request(url)


class AsyncMockTransport(BaseMockTransport, httpcore.AsyncHTTPTransport):
    def __init__(self, num_failures: int) -> None:
        super().__init__(num_failures)

    async def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: Mapping[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream]:
        return self._request(url)


def test_no_retries() -> None:
    """
    By default, connection failures are not retried on.
    """
    transport = MockTransport(num_failures=1)
    client = httpx.Client(transport=transport)

    response = client.get("https://example.com")
    assert response.status_code == 200

    with pytest.raises(httpx.ConnectTimeout):
        client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        client.get("https://example.com/connect_error")


def test_retries_enabled() -> None:
    """
    When retries are enabled, connection failures are retried on with
    a fixed exponential backoff.
    """
    transport = MockTransport(num_failures=3)
    client = httpx.Client(transport=transport, retries=3)
    expected_elapsed_time = pytest.approx(0 + 0.5 + 1, rel=0.1)

    response = client.get("https://example.com")
    assert response.status_code == 200

    response = client.get("https://example.com/connect_timeout")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == expected_elapsed_time

    response = client.get("https://example.com/connect_error")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == expected_elapsed_time

    with pytest.raises(httpx.ReadTimeout):
        client.get("https://example.com/read_timeout")

    with pytest.raises(httpx.NetworkError):
        client.get("https://example.com/network_error")


@pytest.mark.usefixtures("async_environment")
async def test_retries_enabled_async() -> None:
    # For test coverage purposes.
    transport = AsyncMockTransport(num_failures=3)
    client = httpx.AsyncClient(transport=transport, retries=3)
    expected_elapsed_time = pytest.approx(0 + 0.5 + 1, rel=0.1)

    # Connect exceptions are retried on with a backoff.
    response = await client.get("https://example.com/connect_timeout")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == expected_elapsed_time

    # Non-connect errors are not retried on.
    with pytest.raises(httpx.ReadTimeout):
        await client.get("https://example.com/read_timeout")

    # Non-idempotent methods are not retried on.
    with pytest.raises(httpx.ConnectTimeout):
        await client.post("https://example.com/connect_timeout")


def test_retries_exceeded() -> None:
    """
    When retries are enabled and connecting failures more than the configured number
    of retries, connect exceptions are raised.
    """
    transport = MockTransport(num_failures=2)
    client = httpx.Client(transport=transport, retries=1)

    with pytest.raises(httpx.ConnectTimeout):
        client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        client.get("https://example.com/connect_error")


@pytest.mark.parametrize("method", ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])
def test_retries_idempotent_methods(method: str) -> None:
    """
    Client can retry on idempotent HTTP methods.
    """
    transport = MockTransport(num_failures=1)
    client = httpx.Client(transport=transport, retries=1)
    response = client.request(method, "https://example.com/connect_timeout")
    assert response.status_code == 200


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_retries_disabled_on_non_idempotent_methods(method: str) -> None:
    """
    Client makes no retries for HTTP methods that are not idempotent.
    """
    transport = MockTransport(num_failures=1)
    client = httpx.Client(transport=transport, retries=2)

    with pytest.raises(httpx.ConnectTimeout):
        client.request(method, "https://example.com/connect_timeout")


@pytest.mark.parametrize(
    "factor, expected",
    [
        (0.1, [0, 0.1, 0.2, 0.4, 0.8]),
        (0.2, [0, 0.2, 0.4, 0.8, 1.6]),
        (0.5, [0, 0.5, 1.0, 2.0, 4.0]),
    ],
)
def test_exponential_backoff(factor: float, expected: List[int]) -> None:
    """
    Exponential backoff helper works as expected.
    """
    delays = list(itertools.islice(exponential_backoff(factor), 5))
    assert delays == expected
