import pytest

import httpcore


@pytest.mark.asyncio
async def test_read_timeout(server):
    timeout = httpcore.TimeoutConfig(read_timeout=0.0001)

    async with httpcore.ConnectionPool(timeout=timeout) as client:
        with pytest.raises(httpcore.ReadTimeout):
            request = httpcore.Request("GET", "http://127.0.0.1:8000/slow_response")
            await client.send(request)


@pytest.mark.asyncio
async def test_connect_timeout(server):
    timeout = httpcore.TimeoutConfig(connect_timeout=0.0001)

    async with httpcore.ConnectionPool(timeout=timeout) as client:
        with pytest.raises(httpcore.ConnectTimeout):
            # See https://stackoverflow.com/questions/100841/
            request = httpcore.Request("GET", "http://10.255.255.1/")
            await client.send(request)


@pytest.mark.asyncio
async def test_pool_timeout(server):
    timeout = httpcore.TimeoutConfig(pool_timeout=0.0001)
    limits = httpcore.PoolLimits(hard_limit=1)

    async with httpcore.ConnectionPool(timeout=timeout, limits=limits) as client:
        request = httpcore.Request("GET", "http://127.0.0.1:8000/")
        response = await client.send(request, stream=True)

        with pytest.raises(httpcore.PoolTimeout):
            request = httpcore.Request("GET", "http://127.0.0.1:8000/")
            await client.send(request)

        await response.read()
