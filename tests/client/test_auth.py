import json
from urllib.parse import parse_qs

import pytest

from httpcore import (
    URL,
    Client,
    Dispatcher,
    Request,
    Response,
    SSLConfig,
    TimeoutConfig,
)


class MockDispatch(Dispatcher):
    async def send(
        self,
        request: Request,
        stream: bool = False,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        body = json.dumps({"auth": request.headers['Authorization']}).encode()
        return Response(200, content=body, request=request)


def test_basic_auth():
    url = "https://example.org/"
    auth = ('tomchristie', 'password123')

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert json.loads(response.text) == {'auth': 'Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM='}


def test_custom_auth():
    url = "https://example.org/"

    def auth(request):
        request.headers['Authorization'] = 'Token 123'
        return request

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert json.loads(response.text) == {'auth': 'Token 123'}
