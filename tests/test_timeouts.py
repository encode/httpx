import pytest
import sys

from httpx import (
    AsyncClient,
    AsyncioBackend,
    Client,
    ConnectTimeout,
    PoolLimits,
    PoolTimeout,
    ReadTimeout,
    TimeoutConfig,
    WriteTimeout,
)


async def test_read_timeout(server, backend):
    timeout = TimeoutConfig(read_timeout=1e-6)

    async with AsyncClient(timeout=timeout, backend=backend) as client:
        with pytest.raises(ReadTimeout):
            await client.get(server.url.copy_with(path="/slow_response"))


async def test_write_timeout(server, backend):
    if sys.platform == "win32" and sys.version_info[:2] <= (3, 6):
        if isinstance(backend, AsyncioBackend):
            pytest.skip()
    timeout = TimeoutConfig(write_timeout=1e-6)

    async with AsyncClient(timeout=timeout, backend=backend) as client:
        with pytest.raises(WriteTimeout):
            data = b"*" * 1024 * 1024 * 100
            await client.put(server.url.copy_with(path="/slow_response"), data=data)


async def test_connect_timeout(server, backend):
    timeout = TimeoutConfig(connect_timeout=1e-6)

    async with AsyncClient(timeout=timeout, backend=backend) as client:
        with pytest.raises(ConnectTimeout):
            # See https://stackoverflow.com/questions/100841/
            await client.get("http://10.255.255.1/")


async def test_pool_timeout(server, backend):
    pool_limits = PoolLimits(hard_limit=1, pool_timeout=1e-4)

    async with AsyncClient(pool_limits=pool_limits, backend=backend) as client:
        response = await client.get(server.url, stream=True)

        with pytest.raises(PoolTimeout):
            await client.get("http://localhost:8000/")

        await response.read()


def test_sync_infinite_timeout(server):
    """Regression test for a bug that occurred under Python 3.6.

    See: https://github.com/encode/httpx/issues/382
    """
    no_timeout = TimeoutConfig()
    with Client(timeout=no_timeout) as client:
        client.get(server.url.copy_with(path="/slow_response/50"))
