import httpx
import pytest


def hello_world(request):
    content = httpx.Text('Hello, world.')
    return httpx.Response(200, content=content)


@pytest.fixture
def server():
    with httpx.serve_http(hello_world) as server:
        yield server


def test_connection_pool_request(server):
    with httpx.ConnectionPool() as pool:
        assert repr(pool) == "<ConnectionPool [0 active]>"
        assert len(pool.connections) == 0

        r = pool.request("GET", server.url)

        assert r.status_code == 200
        assert repr(pool) == "<ConnectionPool [0 active, 1 idle]>"
        assert len(pool.connections) == 1


def test_connection_pool_connection_close(server):
    with httpx.ConnectionPool() as pool:
        assert repr(pool) == "<ConnectionPool [0 active]>"
        assert len(pool.connections) == 0

        r = pool.request("GET", server.url, headers={"Connection": "close"})

        # TODO: Really we want closed connections proactively removed from the pool,
        assert r.status_code == 200
        assert repr(pool) == "<ConnectionPool [0 active, 1 closed]>"
        assert len(pool.connections) == 1


def test_connection_pool_stream(server):
    with httpx.ConnectionPool() as pool:
        assert repr(pool) == "<ConnectionPool [0 active]>"
        assert len(pool.connections) == 0

        with pool.stream("GET", server.url) as r:
            assert r.status_code == 200
            assert repr(pool) == "<ConnectionPool [1 active]>"
            assert len(pool.connections) == 1
            r.read()

        assert repr(pool) == "<ConnectionPool [0 active, 1 idle]>"
        assert len(pool.connections) == 1


def test_connection_pool_cannot_request_after_closed(server):
    with httpx.ConnectionPool() as pool:
        pool

    with pytest.raises(RuntimeError):
        pool.request("GET", server.url)


def test_connection_pool_should_have_managed_lifespan(server):
    pool = httpx.ConnectionPool()
    with pytest.warns(UserWarning):
        del pool


def test_connection_request(server):
    with httpx.open_connection(server.url) as conn:
        assert repr(conn) == f"<Connection [{server.url} idle]>"

        r = conn.request("GET", "/")

        assert r.status_code == 200
        assert repr(conn) == f"<Connection [{server.url} idle]>"


def test_connection_stream(server):
    with httpx.open_connection(server.url) as conn:
        assert repr(conn) == f"<Connection [{server.url} idle]>"
        with conn.stream("GET", "/") as r:
            assert r.status_code == 200
            assert repr(conn) == f"<Connection [{server.url} active]>"
            r.read()
        assert repr(conn) == f"<Connection [{server.url} idle]>"


# # with httpx.open_connection("https://www.example.com/") as conn:
# #     r = conn.request("GET", "/")

# # >>> pool = httpx.ConnectionPool()
# # >>> pool
# # <ConnectionPool [0 active]>

# # >>> with httpx.open_connection_pool() as pool:
# # >>>     res = pool.request("GET", "https://www.example.com")
# # >>>     res, pool
# # <Response [200 OK]>, <ConnectionPool [1 idle]>

# # >>> with httpx.open_connection_pool() as pool:
# # >>>     with pool.stream("GET", "https://www.example.com") as res:
# # >>>         res, pool
# # <Response [200 OK]>, <ConnectionPool [1 active]>

# # >>> with httpx.open_connection_pool() as pool:
# # >>>     req = httpx.Request("GET", "https://www.example.com")
# # >>>     with pool.send(req) as res:
# # >>>         res.body()
# # >>>     res, pool
# # <Response [200 OK]>, <ConnectionPool [1 idle]>

# # >>> with httpx.open_connection_pool() as pool:
# # >>>     pool.close()
# # <ConnectionPool [0 active]>

# # with httpx.open_connection("https://www.example.com/") as conn:
# #     with conn.upgrade("GET", "/feed", {"Upgrade": "WebSocket") as stream:
# #         ...

# # with httpx.open_connection("http://127.0.0.1:8080") as conn:
# #     with conn.upgrade("CONNECT", "www.encode.io:443") as stream:
# #         stream.start_tls(ctx, hostname="www.encode.io")
# #         ...

