import hashlib
import os
import typing

import httpcore
import pytest

from httpx import (
    URL,
    AsyncClient,
    Auth,
    BasicAuth,
    Client,
    DigestAuth,
    ProtocolError,
    Request,
    RequestBodyUnavailable,
    Response,
)
from httpx._content_streams import ContentStream, JSONStream

from ..common import FIXTURES_DIR


def get_header_value(headers, key, default=None):
    lookup = key.encode("ascii").lower()
    for header_key, header_value in headers:
        if header_key.lower() == lookup:
            return header_value.decode("ascii")
    return default


class MockTransport:
    def __init__(self, auth_header: bytes = b"", status_code: int = 200) -> None:
        self.auth_header = auth_header
        self.status_code = status_code

    def _request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, int, bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: typing.Mapping[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        authorization = get_header_value(headers, "Authorization")
        response_headers = (
            [(b"www-authenticate", self.auth_header)] if self.auth_header else []
        )
        response_stream = JSONStream({"auth": authorization})
        return b"HTTP/1.1", self.status_code, b"", response_headers, response_stream


class AsyncMockTransport(MockTransport, httpcore.AsyncHTTPTransport):
    async def request(
        self, *args, **kwargs
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        return self._request(*args, **kwargs)


class SyncMockTransport(MockTransport, httpcore.SyncHTTPTransport):
    def request(
        self, *args, **kwargs
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        return self._request(*args, **kwargs)


class MockDigestAuthTransport(httpcore.AsyncHTTPTransport):
    def __init__(
        self,
        algorithm: str = "SHA-256",
        send_response_after_attempt: int = 1,
        qop: str = "auth",
        regenerate_nonce: bool = True,
    ) -> None:
        self.algorithm = algorithm
        self.send_response_after_attempt = send_response_after_attempt
        self.qop = qop
        self._regenerate_nonce = regenerate_nonce
        self._response_count = 0

    async def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: httpcore.AsyncByteStream = None,
        timeout: typing.Mapping[str, typing.Optional[float]] = None,
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        if self._response_count < self.send_response_after_attempt:
            assert headers is not None
            return self.challenge_send(method, headers)

        authorization = get_header_value(headers, "Authorization")
        body = JSONStream({"auth": authorization})
        return b"HTTP/1.1", 200, b"", [], body

    def challenge_send(
        self, method: bytes, headers: typing.List[typing.Tuple[bytes, bytes]]
    ) -> typing.Tuple[
        bytes, int, bytes, typing.List[typing.Tuple[bytes, bytes]], ContentStream
    ]:
        self._response_count += 1
        nonce = (
            hashlib.sha256(os.urandom(8)).hexdigest()
            if self._regenerate_nonce
            else "ee96edced2a0b43e4869e96ebe27563f369c1205a049d06419bb51d8aeddf3d3"
        )
        challenge_data = {
            "nonce": nonce,
            "qop": self.qop,
            "opaque": (
                "ee6378f3ee14ebfd2fff54b70a91a7c9390518047f242ab2271380db0e14bda1"
            ),
            "algorithm": self.algorithm,
            "stale": "FALSE",
        }
        challenge_str = ", ".join(
            '{}="{}"'.format(key, value)
            for key, value in challenge_data.items()
            if value
        )

        headers = [
            (
                b"www-authenticate",
                b'Digest realm="httpx@example.org", ' + challenge_str.encode("ascii"),
            )
        ]
        return b"HTTP/1.1", 401, b"", headers, ContentStream()


class RepeatAuth(Auth):
    """
    A mock authentication scheme that requires clients to send
    the request a fixed number of times, and then send a last request containing
    an aggregation of nonces that the server sent in 'WWW-Authenticate' headers
    of intermediate responses.
    """

    requires_request_body = True

    def __init__(self, repeat: int):
        self.repeat = repeat

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        nonces = []

        for index in range(self.repeat):
            request.headers["Authorization"] = f"Repeat {index}"
            response = yield request
            nonces.append(response.headers["www-authenticate"])

        key = ".".join(nonces)
        request.headers["Authorization"] = f"Repeat {key}"
        yield request


class ResponseBodyAuth(Auth):
    """
    A mock authentication scheme that requires clients to send an 'Authorization'
    header, then send back the contents of the response in the 'Authorization'
    header.
    """

    requires_response_body = True

    def __init__(self, token):
        self.token = token

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        request.headers["Authorization"] = self.token
        response = yield request
        data = response.text
        request.headers["Authorization"] = data
        yield request


@pytest.mark.asyncio
async def test_basic_auth() -> None:
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


@pytest.mark.asyncio
async def test_basic_auth_in_url() -> None:
    url = "https://tomchristie:password123@example.org/"

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


@pytest.mark.asyncio
async def test_basic_auth_on_session() -> None:
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    client = AsyncClient(transport=AsyncMockTransport(), auth=auth)
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


@pytest.mark.asyncio
async def test_custom_auth() -> None:
    url = "https://example.org/"

    def auth(request: Request) -> Request:
        request.headers["Authorization"] = "Token 123"
        return request

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Token 123"}


@pytest.mark.asyncio
async def test_netrc_auth() -> None:
    os.environ["NETRC"] = str(FIXTURES_DIR / ".netrc")
    url = "http://netrcexample.org"

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }


@pytest.mark.asyncio
async def test_auth_header_has_priority_over_netrc() -> None:
    os.environ["NETRC"] = str(FIXTURES_DIR / ".netrc")
    url = "http://netrcexample.org"

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url, headers={"Authorization": "Override"})

    assert response.status_code == 200
    assert response.json() == {"auth": "Override"}


@pytest.mark.asyncio
async def test_trust_env_auth() -> None:
    os.environ["NETRC"] = str(FIXTURES_DIR / ".netrc")
    url = "http://netrcexample.org"

    client = AsyncClient(transport=AsyncMockTransport(), trust_env=False)
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": None}

    client = AsyncClient(transport=AsyncMockTransport(), trust_env=True)
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }


@pytest.mark.asyncio
async def test_auth_disable_per_request() -> None:
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    client = AsyncClient(transport=AsyncMockTransport(), auth=auth)
    response = await client.get(url, auth=None)

    assert response.status_code == 200
    assert response.json() == {"auth": None}


def test_auth_hidden_url() -> None:
    url = "http://example-username:example-password@example.org/"
    expected = "URL('http://example-username:[secure]@example.org/')"
    assert url == URL(url)
    assert expected == repr(URL(url))


@pytest.mark.asyncio
async def test_auth_hidden_header() -> None:
    url = "https://example.org/"
    auth = ("example-username", "example-password")

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url, auth=auth)

    assert "'authorization': '[secure]'" in str(response.request.headers)


@pytest.mark.asyncio
async def test_auth_property() -> None:
    client = AsyncClient(transport=AsyncMockTransport())
    assert client.auth is None

    client.auth = ("tomchristie", "password123")  # type: ignore
    assert isinstance(client.auth, BasicAuth)

    url = "https://example.org/"
    response = await client.get(url)
    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


@pytest.mark.asyncio
async def test_auth_invalid_type() -> None:
    with pytest.raises(TypeError):
        client = AsyncClient(
            transport=AsyncMockTransport(),
            auth="not a tuple, not a callable",  # type: ignore
        )

    client = AsyncClient(transport=AsyncMockTransport())

    with pytest.raises(TypeError):
        await client.get(auth="not a tuple, not a callable")  # type: ignore

    with pytest.raises(TypeError):
        client.auth = "not a tuple, not a callable"  # type: ignore


@pytest.mark.asyncio
async def test_digest_auth_returns_no_auth_if_no_digest_header_in_response() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    client = AsyncClient(transport=AsyncMockTransport())
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": None}
    assert len(response.history) == 0


@pytest.mark.asyncio
async def test_digest_auth_200_response_including_digest_auth_header() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    auth_header = b'Digest realm="realm@host.com",qop="auth",nonce="abc",opaque="xyz"'

    client = AsyncClient(
        transport=AsyncMockTransport(auth_header=auth_header, status_code=200)
    )
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": None}
    assert len(response.history) == 0


@pytest.mark.asyncio
async def test_digest_auth_401_response_without_digest_auth_header() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    client = AsyncClient(transport=AsyncMockTransport(auth_header=b"", status_code=401))
    response = await client.get(url, auth=auth)

    assert response.status_code == 401
    assert response.json() == {"auth": None}
    assert len(response.history) == 0


@pytest.mark.parametrize(
    "algorithm,expected_hash_length,expected_response_length",
    [
        ("MD5", 64, 32),
        ("MD5-SESS", 64, 32),
        ("SHA", 64, 40),
        ("SHA-SESS", 64, 40),
        ("SHA-256", 64, 64),
        ("SHA-256-SESS", 64, 64),
        ("SHA-512", 64, 128),
        ("SHA-512-SESS", 64, 128),
    ],
)
@pytest.mark.asyncio
async def test_digest_auth(
    algorithm: str, expected_hash_length: int, expected_response_length: int
) -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    client = AsyncClient(transport=MockDigestAuthTransport(algorithm=algorithm))
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert len(response.history) == 1

    authorization = typing.cast(dict, response.json())["auth"]
    scheme, _, fields = authorization.partition(" ")
    assert scheme == "Digest"

    response_fields = [field.strip() for field in fields.split(",")]
    digest_data = dict(field.split("=") for field in response_fields)

    assert digest_data["username"] == '"tomchristie"'
    assert digest_data["realm"] == '"httpx@example.org"'
    assert "nonce" in digest_data
    assert digest_data["uri"] == '"/"'
    assert len(digest_data["response"]) == expected_response_length + 2  # extra quotes
    assert len(digest_data["opaque"]) == expected_hash_length + 2
    assert digest_data["algorithm"] == algorithm
    assert digest_data["qop"] == "auth"
    assert digest_data["nc"] == "00000001"
    assert len(digest_data["cnonce"]) == 16 + 2


@pytest.mark.asyncio
async def test_digest_auth_no_specified_qop() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    client = AsyncClient(transport=MockDigestAuthTransport(qop=""))
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert len(response.history) == 1

    authorization = typing.cast(dict, response.json())["auth"]
    scheme, _, fields = authorization.partition(" ")
    assert scheme == "Digest"

    response_fields = [field.strip() for field in fields.split(",")]
    digest_data = dict(field.split("=") for field in response_fields)

    assert "qop" not in digest_data
    assert "nc" not in digest_data
    assert "cnonce" not in digest_data
    assert digest_data["username"] == '"tomchristie"'
    assert digest_data["realm"] == '"httpx@example.org"'
    assert len(digest_data["nonce"]) == 64 + 2  # extra quotes
    assert digest_data["uri"] == '"/"'
    assert len(digest_data["response"]) == 64 + 2
    assert len(digest_data["opaque"]) == 64 + 2
    assert digest_data["algorithm"] == "SHA-256"


@pytest.mark.parametrize("qop", ("auth, auth-int", "auth,auth-int", "unknown,auth"))
@pytest.mark.asyncio
async def test_digest_auth_qop_including_spaces_and_auth_returns_auth(qop: str) -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    client = AsyncClient(transport=MockDigestAuthTransport(qop=qop))
    response = await client.get(url, auth=auth)

    assert response.status_code == 200
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_digest_auth_qop_auth_int_not_implemented() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    client = AsyncClient(transport=MockDigestAuthTransport(qop="auth-int"))

    with pytest.raises(NotImplementedError):
        await client.get(url, auth=auth)


@pytest.mark.asyncio
async def test_digest_auth_qop_must_be_auth_or_auth_int() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    client = AsyncClient(transport=MockDigestAuthTransport(qop="not-auth"))

    with pytest.raises(ProtocolError):
        await client.get(url, auth=auth)


@pytest.mark.asyncio
async def test_digest_auth_incorrect_credentials() -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    client = AsyncClient(
        transport=MockDigestAuthTransport(send_response_after_attempt=2)
    )
    response = await client.get(url, auth=auth)

    assert response.status_code == 401
    assert len(response.history) == 1


@pytest.mark.parametrize(
    "auth_header",
    [
        b'Digest realm="httpx@example.org", qop="auth"',  # missing fields
        b'realm="httpx@example.org", qop="auth"',  # not starting with Digest
        b'DigestZ realm="httpx@example.org", qop="auth"'
        b'qop="auth,auth-int",nonce="abc",opaque="xyz"',
        b'Digest realm="httpx@example.org", qop="auth,au',  # malformed fields list
    ],
)
@pytest.mark.asyncio
async def test_async_digest_auth_raises_protocol_error_on_malformed_header(
    auth_header: bytes,
) -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    client = AsyncClient(
        transport=AsyncMockTransport(auth_header=auth_header, status_code=401)
    )

    with pytest.raises(ProtocolError):
        await client.get(url, auth=auth)


@pytest.mark.parametrize(
    "auth_header",
    [
        b'Digest realm="httpx@example.org", qop="auth"',  # missing fields
        b'realm="httpx@example.org", qop="auth"',  # not starting with Digest
        b'DigestZ realm="httpx@example.org", qop="auth"'
        b'qop="auth,auth-int",nonce="abc",opaque="xyz"',
        b'Digest realm="httpx@example.org", qop="auth,au',  # malformed fields list
    ],
)
def test_sync_digest_auth_raises_protocol_error_on_malformed_header(
    auth_header: bytes,
) -> None:
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    client = Client(
        transport=SyncMockTransport(auth_header=auth_header, status_code=401)
    )

    with pytest.raises(ProtocolError):
        client.get(url, auth=auth)


@pytest.mark.asyncio
async def test_async_auth_history() -> None:
    """
    Test that intermediate requests sent as part of an authentication flow
    are recorded in the response history.
    """
    url = "https://example.org/"
    auth = RepeatAuth(repeat=2)
    client = AsyncClient(transport=AsyncMockTransport(auth_header=b"abc"))

    response = await client.get(url, auth=auth)
    assert response.status_code == 200
    assert response.json() == {"auth": "Repeat abc.abc"}

    assert len(response.history) == 2
    resp1, resp2 = response.history
    assert resp1.json() == {"auth": "Repeat 0"}
    assert resp2.json() == {"auth": "Repeat 1"}

    assert len(resp2.history) == 1
    assert resp2.history == [resp1]

    assert len(resp1.history) == 0


def test_sync_auth_history() -> None:
    """
    Test that intermediate requests sent as part of an authentication flow
    are recorded in the response history.
    """
    url = "https://example.org/"
    auth = RepeatAuth(repeat=2)
    client = Client(transport=SyncMockTransport(auth_header=b"abc"))

    response = client.get(url, auth=auth)
    assert response.status_code == 200
    assert response.json() == {"auth": "Repeat abc.abc"}

    assert len(response.history) == 2
    resp1, resp2 = response.history
    assert resp1.json() == {"auth": "Repeat 0"}
    assert resp2.json() == {"auth": "Repeat 1"}

    assert len(resp2.history) == 1
    assert resp2.history == [resp1]

    assert len(resp1.history) == 0


@pytest.mark.asyncio
async def test_digest_auth_unavailable_streaming_body():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    client = AsyncClient(transport=AsyncMockTransport())

    async def streaming_body():
        yield b"Example request body"  # pragma: nocover

    with pytest.raises(RequestBodyUnavailable):
        await client.post(url, data=streaming_body(), auth=auth)


@pytest.mark.asyncio
async def test_async_auth_reads_response_body() -> None:
    """
    Test that we can read the response body in an auth flow if `requires_response_body`
    is set.
    """
    url = "https://example.org/"
    auth = ResponseBodyAuth("xyz")
    client = AsyncClient(transport=AsyncMockTransport())

    response = await client.get(url, auth=auth)
    assert response.status_code == 200
    assert response.json() == {"auth": '{"auth": "xyz"}'}


def test_sync_auth_reads_response_body() -> None:
    """
    Test that we can read the response body in an auth flow if `requires_response_body`
    is set.
    """
    url = "https://example.org/"
    auth = ResponseBodyAuth("xyz")
    client = Client(transport=SyncMockTransport())

    response = client.get(url, auth=auth)
    assert response.status_code == 200
    assert response.json() == {"auth": '{"auth": "xyz"}'}
