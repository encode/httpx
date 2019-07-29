import json

import pytest

from httpx import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    BasicAuthBase,
    CertTypes,
    Client,
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
    class CustomBasicAuth(BasicAuthBase):
        def build_auth_header(self) -> str:
            return "Token 123"

    url = "https://example.org/"
    auth = CustomBasicAuth()

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Token 123"}


def test_bad_custom_basic_auth():
    class BadAuth:
        pass

    url = "https://example.org/"
    auth = BadAuth()

    with Client(dispatch=MockDispatch()) as client:
        with pytest.raises(
            TypeError, match="Invalid type for auth. Expected: BasicAuthBase."
        ):
            client.get(url, auth=auth)
