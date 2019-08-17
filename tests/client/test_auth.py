import json
import os

from httpx import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
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
    url = "https://example.org/"

    def auth(request):
        request.headers["Authorization"] = "Token 123"
        return request

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Token 123"}


def test_netrc_auth():
    os.environ["NETRC"] = "tests/.netrc"
    url = "http://netrcexample.org"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }


def test_trust_env_auth():
    os.environ["NETRC"] = "tests/.netrc"
    url = "http://netrcexample.org"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, trust_env=False)

    assert response.status_code == 200
    assert response.json() == {"auth": None}

    # Test that the setting at the request() level overrides client. 
    with Client(dispatch=MockDispatch(), trust_env=False) as client:
        response = client.get(url, trust_env=True)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }
