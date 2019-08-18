import pytest

import httpx


async def test_keepalive_connections(server, backend):
    """
    Connections should default to staying in a keep-alive state.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


async def test_differing_connection_keys(server, backend):
    """
    Connections to differing connection keys should result in multiple connections.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://localhost:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 2


async def test_soft_limit(server, backend):
    """
    The soft_limit config should limit the maximum number of keep-alive connections.
    """
    pool_limits = httpx.PoolLimits(soft_limit=1)

    async with httpx.ConnectionPool(pool_limits=pool_limits, backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://localhost:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


async def test_streaming_response_holds_connection(server, backend):
    """
    A streaming request should hold the connection open until the response is read.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 0

        await response.read()

        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


async def test_multiple_concurrent_connections(server, backend):
    """
    Multiple conncurrent requests should open multiple conncurrent connections.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response_a = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 0

        response_b = await http.request("GET", "http://127.0.0.1:8000/")
        assert len(http.active_connections) == 2
        assert len(http.keepalive_connections) == 0

        await response_b.read()
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 1

        await response_a.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 2


async def test_close_connections(server, backend):
    """
    Using a `Connection: close` header should close the connection.
    """
    headers = [(b"connection", b"close")]
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/", headers=headers)
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0


async def test_standard_response_close(server, backend):
    """
    A standard close should keep the connection open.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        await response.close()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


async def test_premature_response_close(server, backend):
    """
    A premature close should close the connection.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.close()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0


async def test_keepalive_connection_closed_by_server_is_reestablished(server, backend):
    """
    Upon keep-alive connection closed by remote a new connection
    should be reestablished.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()

        # shutdown the server to close the keep-alive connection
        await server.shutdown()
        await server.startup()

        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


async def test_keepalive_http2_connection_closed_by_server_is_reestablished(
    server, backend
):
    """
    Upon keep-alive connection closed by remote a new connection
    should be reestablished.
    """
    async with httpx.ConnectionPool(backend=backend) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()

        # shutdown the server to close the keep-alive connection
        await server.shutdown()
        await server.startup()

        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.asyncio
async def test_connection_closed_free_semaphore_on_acquire(server):
    """
    Verify that max_connections semaphore is released
    properly on a disconnected connection.
    """
    async with httpx.ConnectionPool(pool_limits=httpx.PoolLimits(hard_limit=1)) as http:
        response = await http.request("GET", "http://127.0.0.1:8000/")
        await response.read()

        # Close the connection so we're forced to recycle it
        await server.shutdown()
        await server.startup()

        response = await http.request("GET", "http://127.0.0.1:8000/")
        assert response.status_code == 200
