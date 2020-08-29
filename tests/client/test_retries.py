import collections
import itertools
from typing import Dict, List, Mapping, Optional, Tuple

import httpcore
import pytest

import httpx
from httpx._utils import exponential_backoff


def test_retries_config() -> None:
    client = httpx.AsyncClient()
    assert client.connect_retries == 0

    client = httpx.AsyncClient(connect_retries=3)
    assert client.connect_retries == 3

    client.connect_retries = 1
    assert client.connect_retries == 1


class AsyncMockTransport(httpcore.AsyncHTTPTransport):
    def __init__(self, num_failures: int) -> None:
        self._num_failures = num_failures
        self._failures_by_path: Dict[bytes, int] = collections.defaultdict(int)

    async def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: Mapping[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream]:
        scheme, host, port, path = url

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

        if self._failures_by_path[path] >= self._num_failures:
            stream = httpcore.PlainByteStream(b"")
            return (b"HTTP/1.1", 200, b"OK", [], stream)

        self._failures_by_path[path] += 1

        raise exc


@pytest.mark.usefixtures("async_environment")
async def test_no_connect_retries() -> None:
    """
    By default, connection failures are not retried on.
    """
    client = httpx.AsyncClient(transport=AsyncMockTransport(num_failures=1))

    response = await client.get("https://example.com")
    assert response.status_code == 200

    with pytest.raises(httpx.ConnectTimeout):
        await client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        await client.get("https://example.com/connect_error")


@pytest.mark.usefixtures("async_environment")
async def test_connect_retries_enabled() -> None:
    """
    When connect retries are enabled, connection failures are retried on with
    a fixed exponential backoff.
    """
    transport = AsyncMockTransport(num_failures=3)
    client = httpx.AsyncClient(transport=transport, connect_retries=3)
    expected_elapsed_time = pytest.approx(0 + 0.5 + 1, rel=0.1)

    response = await client.get("https://example.com")
    assert response.status_code == 200

    response = await client.get("https://example.com/connect_timeout")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == expected_elapsed_time

    response = await client.get("https://example.com/connect_error")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == expected_elapsed_time

    with pytest.raises(httpx.ReadTimeout):
        await client.get("https://example.com/read_timeout")

    with pytest.raises(httpx.NetworkError):
        await client.get("https://example.com/network_error")


@pytest.mark.usefixtures("async_environment")
async def test_connect_retries_exceeded() -> None:
    """
    When retries are enabled and connecting failures more than the configured number
    of retries, connect exceptions are raised.
    """
    transport = AsyncMockTransport(num_failures=2)
    client = httpx.AsyncClient(transport=transport, connect_retries=1)

    with pytest.raises(httpx.ConnectTimeout):
        await client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        await client.get("https://example.com/connect_error")


@pytest.mark.usefixtures("async_environment")
@pytest.mark.parametrize("method", ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])
async def test_connect_retries_idempotent_methods(method: str) -> None:
    """
    Client can retry on idempotent HTTP methods.
    """
    transport = AsyncMockTransport(num_failures=1)
    client = httpx.AsyncClient(transport=transport, connect_retries=1)
    response = await client.request(method, "https://example.com/connect_timeout")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_connect_retries_disabled_on_non_idempotent_methods(method: str) -> None:
    """
    Client makes no retries for HTTP methods that are not idempotent.
    """
    transport = AsyncMockTransport(num_failures=1)
    client = httpx.AsyncClient(transport=transport, connect_retries=2)

    with pytest.raises(httpx.ConnectTimeout):
        await client.request(method, "https://example.com/connect_timeout")


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
