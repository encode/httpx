from httpx import HTTPConnection


async def test_get(server, backend):
    conn = HTTPConnection(origin="http://127.0.0.1:8000/", backend=backend)
    response = await conn.request("GET", "http://127.0.0.1:8000/")
    await response.read()
    assert response.status_code == 200
    assert response.content == b"Hello, world!"


async def test_post(server, backend):
    conn = HTTPConnection(origin="http://127.0.0.1:8000/", backend=backend)
    response = await conn.request(
        "GET", "http://127.0.0.1:8000/", data=b"Hello, world!"
    )
    assert response.status_code == 200


async def test_https_get_with_ssl_defaults(https_server, backend):
    """
    An HTTPS request, with default SSL configuration set on the client.
    """
    conn = HTTPConnection(
        origin="https://127.0.0.1:8001/", verify=False, backend=backend
    )
    response = await conn.request("GET", "https://127.0.0.1:8001/")
    await response.read()
    assert response.status_code == 200
    assert response.content == b"Hello, world!"


async def test_https_get_with_sll_overrides(https_server, backend):
    """
    An HTTPS request, with SSL configuration set on the request.
    """
    conn = HTTPConnection(origin="https://127.0.0.1:8001/", backend=backend)
    response = await conn.request("GET", "https://127.0.0.1:8001/", verify=False)
    await response.read()
    assert response.status_code == 200
    assert response.content == b"Hello, world!"
