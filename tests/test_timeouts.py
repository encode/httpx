import pytest

from httpx import (
    AsyncClient,
    ConnectTimeout,
    PoolLimits,
    PoolTimeout,
    ReadTimeout,
    TimeoutConfig,
    WriteTimeout,
)


async def test_read_timeout(server, backend):
    timeout = TimeoutConfig(read_timeout=0.000001)

    async with AsyncClient(timeout=timeout, backend=backend) as client:
        with pytest.raises(ReadTimeout):
            await client.get("http://127.0.0.1:8000/slow_response")


async def test_write_timeout(server, backend):
    timeout = TimeoutConfig(write_timeout=0.000001)

    async with AsyncClient(timeout=timeout, backend=backend) as client:
        with pytest.raises(WriteTimeout):
            data = b"*" * 1024 * 1024 * 100
            await client.put("http://127.0.0.1:8000/slow_response", data=data)


async def test_connect_timeout(server, backend):
    timeout = TimeoutConfig(connect_timeout=0.000001)

    async with AsyncClient(timeout=timeout, backend=backend) as client:
        with pytest.raises(ConnectTimeout):
            # See https://stackoverflow.com/questions/100841/
            await client.get("http://10.255.255.1/")


async def test_pool_timeout(server, backend):
    pool_limits = PoolLimits(hard_limit=1, pool_timeout=0.000001)

    async with AsyncClient(pool_limits=pool_limits, backend=backend) as client:
        response = await client.get("http://127.0.0.1:8000/", stream=True)

        with pytest.raises(PoolTimeout):
            await client.get("http://localhost:8000/")

        await response.read()
