import collections
import itertools
from typing import List, Tuple, Type, Dict, Mapping, Optional

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
    _ENDPOINTS: Dict[bytes, Tuple[Type[Exception], bool]] = {
        b"/connect_timeout": (httpcore.ConnectTimeout, True),
        b"/connect_error": (httpcore.ConnectError, True),
        b"/read_timeout": (httpcore.ReadTimeout, False),
        b"/network_error": (httpcore.NetworkError, False),
    }

    def __init__(self, succeed_after: int) -> None:
        self._succeed_after = succeed_after
        self._path_attempts: Dict[bytes, int] = collections.defaultdict(int)

    async def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: Mapping[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream]:
        scheme, host, port, path = url

        if path not in self._ENDPOINTS:
            stream = httpcore.PlainByteStream(b"")
            return (b"HTTP/1.1", 200, b"OK", [], stream)

        exc_cls, is_retryable = self._ENDPOINTS[path]

        if not is_retryable:
            raise exc_cls()

        if self._path_attempts[path] < self._succeed_after:
            self._path_attempts[path] += 1
            raise exc_cls()

        stream = httpcore.PlainByteStream(b"")
        return (b"HTTP/1.1", 200, b"OK", [], stream)


@pytest.mark.usefixtures("async_environment")
async def test_no_retries() -> None:
    client = httpx.AsyncClient(transport=AsyncMockTransport(succeed_after=1))

    response = await client.get("https://example.com")
    assert response.status_code == 200

    with pytest.raises(httpx.ConnectTimeout):
        await client.get("https://example.com/connect_timeout")

    with pytest.raises(httpx.ConnectError):
        await client.get("https://example.com/connect_error")

    with pytest.raises(httpx.ReadTimeout):
        await client.get("https://example.com/read_timeout")

    with pytest.raises(httpx.NetworkError):
        await client.get("https://example.com/network_error")


@pytest.mark.usefixtures("async_environment")
async def test_retries_enabled() -> None:
    transport = AsyncMockTransport(succeed_after=3)
    client = httpx.AsyncClient(
        transport=transport, retries=httpx.Retries(3, backoff_factor=0.01)
    )

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
    transport = AsyncMockTransport(succeed_after=2)
    client = httpx.AsyncClient(transport=transport, retries=1)
    with pytest.raises(httpx.ConnectTimeout):
        await client.get("https://example.com/connect_timeout")


@pytest.mark.usefixtures("async_environment")
@pytest.mark.parametrize("method", ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])
async def test_retries_idempotent_methods(method: str) -> None:
    transport = AsyncMockTransport(succeed_after=1)
    client = httpx.AsyncClient(transport=transport, retries=1)
    response = await client.request(method, "https://example.com/connect_timeout")
    assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_retries_disabled_on_non_idempotent_methods(method: str) -> None:
    """
    Non-idempotent HTTP verbs should never be retried on.
    """
    transport = AsyncMockTransport(succeed_after=1)
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
    delays = list(itertools.islice(exponential_backoff(factor), 5))
    assert delays == expected


@pytest.mark.usefixtures("async_environment")
async def test_retries_backoff() -> None:
    retries = httpx.Retries(3, backoff_factor=0.05)
    transport = AsyncMockTransport(succeed_after=3)
    client = httpx.AsyncClient(transport=transport, retries=retries)
    response = await client.get("https://example.com/connect_timeout")
    assert response.status_code == 200
    assert response.elapsed.total_seconds() == pytest.approx(0 + 0.05 + 0.1, rel=0.1)
