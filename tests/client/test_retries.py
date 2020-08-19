import collections
import itertools
from typing import List, Tuple, Dict, Mapping, Optional

import pytest

import httpcore
import httpx
from httpx._utils import exponential_backoff


def test_retries_config() -> None:
    client = httpx.AsyncClient()
    assert client.retries == httpx.Retries(0)
    assert client.retries.max_attempts == 0

    client = httpx.AsyncClient(retries=3)
    assert client.retries == httpx.Retries(3)
    assert client.retries.max_attempts == 3
    assert client.retries.backoff_factor == 0.2

    client = httpx.AsyncClient(retries=httpx.Retries(3, backoff_factor=0.1))
    assert client.retries == httpx.Retries(3, backoff_factor=0.1)
    assert client.retries.max_attempts == 3
    assert client.retries.backoff_factor == 0.1


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
async def test_no_retries() -> None:
    """
    When no retries are configured, the default behavior is to not retry
    and raise immediately any connection failures.
    """
    client = httpx.AsyncClient(transport=AsyncMockTransport(num_failures=1))

    response = await client.get("https://example.com")
    assert response.status_code == 200

    with pytest.raises(httpx.ConnectTimeout):
        await client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        await client.get("https://example.com/connect_error")


@pytest.mark.usefixtures("async_environment")
async def test_retries_enabled() -> None:
    """
    When retries are enabled, connection failures are retried on.
    """
    transport = AsyncMockTransport(num_failures=3)
    retries = httpx.Retries(
        3,
        # Small backoff to speed up this test.
        backoff_factor=0.01,
    )
    client = httpx.AsyncClient(transport=transport, retries=retries)

    response = await client.get("https://example.com")
    assert response.status_code == 200

    response = await client.get("https://example.com/connect_timeout")
    assert response.status_code == 200

    response = await client.get("https://example.com/connect_error")
    assert response.status_code == 200

    with pytest.raises(httpx.ReadTimeout):
        await client.get("https://example.com/read_timeout")

    with pytest.raises(httpx.NetworkError):
        await client.get("https://example.com/network_error")


@pytest.mark.usefixtures("async_environment")
async def test_retries_exceeded() -> None:
    """
    When retries are enabled and connecting failures more than the configured number
    of retries, connect exceptions are raised.
    """
    transport = AsyncMockTransport(num_failures=2)
    retries = 1
    client = httpx.AsyncClient(transport=transport, retries=retries)

    with pytest.raises(httpx.ConnectTimeout):
        await client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        await client.get("https://example.com/connect_error")


@pytest.mark.usefixtures("async_environment")
@pytest.mark.parametrize("method", ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])
async def test_retries_idempotent_methods(method: str) -> None:
    """
    Client makes retries for all idempotent HTTP methods.
    """
    transport = AsyncMockTransport(num_failures=1)
    retries = 1
    client = httpx.AsyncClient(transport=transport, retries=retries)
    response = await client.request(method, "https://example.com/connect_timeout")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_retries_disabled_on_non_idempotent_methods(method: str) -> None:
    """
    Client makes no retries for HTTP methods that are not idempotent.
    """
    transport = AsyncMockTransport(num_failures=1)
    client = httpx.AsyncClient(transport=transport, retries=2)

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


@pytest.mark.usefixtures("async_environment")
async def test_retries_backoff() -> None:
    """
    Exponential backoff is applied when retrying.
    """
    retries = httpx.Retries(3, backoff_factor=0.05)
    transport = AsyncMockTransport(num_failures=3)
    client = httpx.AsyncClient(transport=transport, retries=retries)
    response = await client.get("https://example.com/connect_timeout")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == pytest.approx(0 + 0.05 + 0.1, rel=0.1)
