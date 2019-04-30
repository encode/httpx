import pytest

import httpcore


@pytest.mark.asyncio
async def test_keepalive_connections(server):
    """
    Connections should default to staying in a keep-alive state.
    """
    async with httpcore.ConnectionPool() as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.asyncio
async def test_differing_connection_keys(server):
    """
    Connnections to differing connection keys should result in multiple connections.
    """
    async with httpcore.ConnectionPool() as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://localhost:8000/")
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 2


@pytest.mark.asyncio
async def test_soft_limit(server):
    """
    The soft_limit config should limit the maximum number of keep-alive connections.
    """
    limits = httpcore.PoolLimits(soft_limit=1)

    async with httpcore.ConnectionPool(limits=limits) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://localhost:8000/")
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.asyncio
async def test_streaming_response_holds_connection(server):
    """
    A streaming request should hold the connection open until the response is read.
    """
    async with httpcore.ConnectionPool() as http:
        response = await http.request("GET", "http://127.0.0.1:8000/", stream=True)
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 0

        await response.read()

        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.asyncio
async def test_multiple_concurrent_connections(server):
    """
    Multiple conncurrent requests should open multiple conncurrent connections.
    """
    async with httpcore.ConnectionPool() as http:
        response_a = await http.request("GET", "http://127.0.0.1:8000/", stream=True)
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 0

        response_b = await http.request("GET", "http://127.0.0.1:8000/", stream=True)
        assert len(http.active_connections) == 2
        assert len(http.keepalive_connections) == 0

        await response_b.read()
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 1

        await response_a.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 2


@pytest.mark.asyncio
async def test_close_connections(server):
    """
    Using a `Connection: close` header should close the connection.
    """
    headers = [(b"connection", b"close")]
    async with httpcore.ConnectionPool() as http:
        response = await http.request("GET", "http://127.0.0.1:8000/", headers=headers)
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0


@pytest.mark.asyncio
async def test_standard_response_close(server):
    """
    A standard close should keep the connection open.
    """
    async with httpcore.ConnectionPool() as http:
        response = await http.request("GET", "http://127.0.0.1:8000/", stream=True)
        await response.read()
        await response.close()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.asyncio
async def test_premature_response_close(server):
    """
    A premature close should close the connection.
    """
    async with httpcore.ConnectionPool() as http:
        response = await http.request("GET", "http://127.0.0.1:8000/", stream=True)
        await response.close()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0
