import pytest

import httpcore


@pytest.mark.asyncio
async def test_read_timeout(server):
    timeout = httpcore.TimeoutConfig(read_timeout=0.0001)

    async with httpcore.ConnectionPool(timeout=timeout) as http:
        with pytest.raises(httpcore.ReadTimeout):
            await http.request("GET", "http://127.0.0.1:8000/slow_response")


@pytest.mark.asyncio
async def test_connect_timeout(server):
    timeout = httpcore.TimeoutConfig(connect_timeout=0.0001)

    async with httpcore.ConnectionPool(timeout=timeout) as http:
        with pytest.raises(httpcore.ConnectTimeout):
            # See https://stackoverflow.com/questions/100841/
            await http.request("GET", "http://10.255.255.1/")


@pytest.mark.asyncio
async def test_pool_timeout(server):
    timeout = httpcore.TimeoutConfig(pool_timeout=0.0001)
    limits = httpcore.PoolLimits(hard_limit=1)

    async with httpcore.ConnectionPool(timeout=timeout, limits=limits) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/", stream=True)

        with pytest.raises(httpcore.PoolTimeout):
            await http.request("GET", "http://127.0.0.1:8000/")

        await response.read()
