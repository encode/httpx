import json

import jwt
import pytest

from httpx import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    HTTPJwtBasicAuth,
    TimeoutTypes,
    VerifyTypes,
)


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


@pytest.mark.parametrize(
    "payload",
    (
        {"a": 1, "b": [1, 2]},
        {"username": "tomchristie", "password": "password123"},
        '{"username": "cansarigol", "password": "123password"}',
    ),
)
def test_jwt_basic_auth(payload):
    url = "https://example.org/"
    auth = HTTPJwtBasicAuth(payload)

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200

    expected_payload = jwt.decode(
        response.json()["auth"].split(" ")[1], "", algorithms=["HS256"]
    )
    if isinstance(payload, str):
        payload = json.loads(payload)
    assert payload == expected_payload


def test_bad_jwt_basic_auth():
    payload = "123"
    with pytest.raises(
        TypeError, match=r".*JWT only supports JSON objects as payloads."
    ):
        HTTPJwtBasicAuth(payload)
