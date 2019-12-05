import pytest

from httpx import (
    Client,
    ConnectTimeout,
    PoolLimits,
    PoolTimeout,
    ReadTimeout,
    Timeout,
    WriteTimeout,
)


async def test_read_timeout(server, backend):
    timeout = Timeout(read_timeout=1e-6)

    async with Client(timeout=timeout, backend=backend) as client:
        with pytest.raises(ReadTimeout):
            await client.get(server.url.copy_with(path="/slow_response"))


async def test_write_timeout(server, backend):
    timeout = Timeout(write_timeout=1e-6)

    async with Client(timeout=timeout, backend=backend) as client:
        with pytest.raises(WriteTimeout):
            data = b"*" * 1024 * 1024 * 100
            await client.put(server.url.copy_with(path="/slow_response"), data=data)


async def test_connect_timeout(server, backend):
    timeout = Timeout(connect_timeout=1e-6)

    async with Client(timeout=timeout, backend=backend) as client:
        with pytest.raises(ConnectTimeout):
            # See https://stackoverflow.com/questions/100841/
            await client.get("http://10.255.255.1/")


async def test_pool_timeout(server, backend):
    pool_limits = PoolLimits(hard_limit=1)
    timeout = Timeout(pool_timeout=1e-4)

    async with Client(
        pool_limits=pool_limits, timeout=timeout, backend=backend
    ) as client:
        async with client.stream("GET", server.url):
            with pytest.raises(PoolTimeout):
                await client.get("http://localhost:8000/")
