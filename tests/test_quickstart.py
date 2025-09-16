import json
import httpx
import pytest


def echo(request):
    request.read()
    response = httpx.Response(200, content=httpx.JSON({
        'method': request.method,
        'query-params': dict(request.url.params.items()),
        'content-type': request.headers.get('Content-Type'),
        'json': json.loads(request.body) if request.body else None,
    }))
    return response


@pytest.fixture
def server():
    with httpx.serve_http(echo) as server:
        yield server


def test_get(server):
    r = httpx.get(server.url)
    assert r.status_code == 200
    assert json.loads(r.body) == {
        'method': 'GET',
        'query-params': {},
        'content-type': None,
        'json': None,
    }


def test_post(server):
    data = httpx.JSON({"data": 123})
    r = httpx.post(server.url, content=data)
    assert r.status_code == 200
    assert json.loads(r.body) == {
        'method': 'POST',
        'query-params': {},
        'content-type': 'application/json',
        'json': {"data": 123},
    }


def test_put(server):
    data = httpx.JSON({"data": 123})
    r = httpx.put(server.url, content=data)
    assert r.status_code == 200
    assert json.loads(r.body) == {
        'method': 'PUT',
        'query-params': {},
        'content-type': 'application/json',
        'json': {"data": 123},
    }


def test_patch(server):
    data = httpx.JSON({"data": 123})
    r = httpx.patch(server.url, content=data)
    assert r.status_code == 200
    assert json.loads(r.body) == {
        'method': 'PATCH',
        'query-params': {},
        'content-type': 'application/json',
        'json': {"data": 123},
    }


def test_delete(server):
    r = httpx.delete(server.url)
    assert r.status_code == 200
    assert json.loads(r.body) == {
        'method': 'DELETE',
        'query-params': {},
        'content-type': None,
        'json': None,
    }
