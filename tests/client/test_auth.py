import json
import os

import pytest

from httpx import (
    URL,
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    TimeoutTypes,
    VerifyTypes,
    HTTPDigestAuth,
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


class MockDigestAuthDispatch(AsyncDispatcher):
    def __init__(self) -> None:
        self._challenge_sent = False

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        if not self._challenge_sent:
            return self.challenge_send(request)

        body = json.dumps({"auth": request.headers.get("Authorization")}).encode()
        return AsyncResponse(200, content=body, request=request)

    def challenge_send(self, request: AsyncRequest) -> AsyncResponse:
        self._challenge_sent = True
        challenge_data = {
            "nonce": "ee96edced2a0b43e4869e96ebe27563f369c1205a049d06419bb51d8aeddf3d3",
            "qop": "auth",
            "opaque": "ee6378f3ee14ebfd2fff54b70a91a7c9390518047f242ab2271380db0e14bda1",
            "algorithm": "SHA-256",
            "stale": "FALSE",
        }
        challenge_str = ", ".join(
            '{}="{}"'.format(key, value) for key, value in challenge_data.items()
        )

        headers = [
            ("www-authenticate", 'Digest realm="httpx@example.org", ' + challenge_str)
        ]
        return AsyncResponse(401, headers=headers, content=b"", request=request)


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

    with Client(dispatch=MockDispatch(), trust_env=False) as client:
        response = client.get(url, trust_env=True)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }


def test_auth_hidden_url():
    url = "http://example-username:example-password@example.org/"
    expected = "URL('http://example-username:[secure]@example.org/')"
    assert url == URL(url)
    assert expected == repr(URL(url))


def test_auth_hidden_header():
    url = "https://example.org/"
    auth = ("example-username", "example-password")

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert "'authorization': '[secure]'" in str(response.request.headers)


def test_auth_invalid_type():
    url = "https://example.org/"
    with Client(dispatch=MockDispatch(), auth="not a tuple, not a callable") as client:
        with pytest.raises(TypeError):
            client.get(url)


def test_digest_auth_returns_no_auth_if_no_digest_header_in_response():
    url = "https://example.org/"
    auth = HTTPDigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": None}


def test_digest_auth():
    url = "https://example.org/"
    auth = HTTPDigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDigestAuthDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    auth = response.json()["auth"]
    assert auth.startswith("Digest")

    response_fields = [field.strip() for field in auth[auth.find(" ") :].split(",")]
    digest_data = dict(field.split("=") for field in response_fields)

    assert digest_data["username"] == '"tomchristie"'
    assert digest_data["realm"] == '"httpx@example.org"'
    assert len(digest_data["nonce"]) == 64 + 2  # extra quotes
    assert digest_data["uri"] == '"/"'
    assert len(digest_data["response"]) == 64 + 2
    assert len(digest_data["opaque"]) == 64 + 2
    assert digest_data["algorithm"] == '"SHA-256"'
    assert digest_data["qop"] == '"auth"'
    assert digest_data["nc"] == '"00000001"'
    assert len(digest_data["cnonce"]) == 16 + 2
