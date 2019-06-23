import json

from http3 import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    TimeoutTypes,
    VerifyTypes,
)
from http3.auth import HTTPBearerAuth


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        body = json.dumps({"auth": request.headers.get("Authorization")}).encode()
        return AsyncResponse(200, content=body, request=request)


def test_basic_auth():
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


def test_basic_auth_in_url():
    url = "https://tomchristie:password123@example.org/"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


def test_basic_auth_on_session():
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    with Client(dispatch=MockDispatch(), auth=auth) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


def test_custom_auth():
    url = "https://example.org/"

    def auth(request):
        request.headers["Authorization"] = "Token 123"
        return request

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Token 123"}


def test_bearer_auth():
    url = "https://example.org/"

    auth = HTTPBearerAuth("token")
    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Bearer token"}


def test_bearer_auth_on_session():
    url = "https://example.org/"

    auth = HTTPBearerAuth("token")
    with Client(dispatch=MockDispatch(), auth=auth) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Bearer token"}
