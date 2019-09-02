import hashlib
import os
import time
import typing
from base64 import b64encode

from ..models import AsyncRequest, AsyncResponse, StatusCode, URL
from .base import BaseMiddleware
from ..utils import safe_encode


class BasicAuthMiddleware(BaseMiddleware):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()

        self.authorization_header = f"Basic {token}"

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request.headers["Authorization"] = self.authorization_header
        return await get_response(request)


class CustomAuthMiddleware(BaseMiddleware):
    def __init__(self, auth: typing.Callable[[AsyncRequest], AsyncRequest]):
        self.auth = auth

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request = self.auth(request)
        return await get_response(request)


class HTTPDigestAuthMiddleware(BaseMiddleware):

    ALGORITHM_TO_HASH_FUNCTION = {
        "MD5": hashlib.md5,
        "MD5-SESS": hashlib.md5,
        "SHA": hashlib.sha1,
        "SHA-SESS": hashlib.sha1,
        "SHA-256": hashlib.sha256,
        "SHA-256-SESS": hashlib.sha256,
        "SHA-512": hashlib.sha512,
        "SHA-512-SESS": hashlib.sha512,
    }

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self.username = username
        self.password = password
        self._previous_nonce: typing.Optional[bytes] = None
        self._nonce_count = 0

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        response = await get_response(request)

        if self._should_return_digest_auth(response):
            auth_header = self._build_auth_header(request, response)
            if auth_header is not None:
                # TODO: raise instead of returning None?
                request.headers["Authorization"] = auth_header
            return await self(request, get_response)

        return response

    def _should_return_digest_auth(self, response: AsyncResponse) -> bool:
        auth_header = response.headers.get("www-authenticate")
        return StatusCode.is_client_error(response.status_code) and (
            auth_header is None or "digest" in auth_header.lower()
        )

    def _expects_digest_auth(self, response: AsyncResponse) -> bool:
        auth_header = response.headers.get("www-authenticate")
        return auth_header is None or "digest" in auth_header.lower()

    def _build_auth_header(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> typing.Optional[str]:
        # Retrieve challenge from response header
        header = response.headers.get("www-authenticate")
        assert header.lower().startswith("digest")
        challenge = self._parse_header(header)
        algorithm = challenge.get("algorithm", "MD5")

        realm = safe_encode(challenge["realm"])
        nonce = safe_encode(challenge["nonce"])
        qop = safe_encode(challenge["qop"]) if "qop" in challenge else None
        opaque = safe_encode(challenge["opaque"]) if "opaque" in challenge else None
        username = safe_encode(self.username)
        password = safe_encode(self.password)

        # Assemble parts depending on hash algorithms
        hash_func = self.ALGORITHM_TO_HASH_FUNCTION[algorithm]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode("utf-8")

        def keyed_digest(secret: bytes, data: bytes) -> bytes:
            return digest(b":".join((secret, data)))

        A1 = b":".join((username, realm, password))
        HA1 = digest(A1)

        path = self._get_parsed_path(request.url)
        A2 = b":".join((request.method.encode("utf-8"), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        # Construct Authenticate header string
        if nonce != self._previous_nonce:
            self._nonce_count = 1
        else:
            self._nonce_count += 1
        self._previous_nonce = nonce
        nc_value = b"%08x" % self._nonce_count

        s = str(self._nonce_count).encode("utf-8")
        s += nonce
        s += time.ctime().encode("utf-8")
        s += os.urandom(8)

        cnonce = hashlib.sha1(s).hexdigest()[:16].encode("utf-8")
        if algorithm.lower().endswith("-sess"):
            A1 += b":".join((nonce, cnonce))

        if algorithm == "MD5-SESS":
            HA1 = digest(b":".join((HA1, nonce, cnonce)))

        if not qop:
            to_key_digest = [nonce, HA2]
        elif qop == "auth" or "auth" in qop.decode().split(","):
            to_key_digest = [nonce, nc_value, cnonce, b"auth", HA2]
        else:
            return None  # handle auth-int

        format_args = {
            "username": username,
            "realm": realm,
            "nonce": nonce,
            "uri": path,
            "response": keyed_digest(HA1, b":".join(to_key_digest)),
        }
        if opaque:
            format_args["opaque"] = opaque
        if algorithm:
            format_args["algorithm"] = algorithm
        if qop:
            format_args["qop"] = "auth"
            format_args["nc"] = nc_value
            format_args["cnonce"] = cnonce

        header_value = ", ".join(
            [
                '{}="{}"'.format(
                    key, value if isinstance(value, str) else value.decode("utf-8")
                )
                for key, value in format_args.items()
            ]
        )
        return "Digest " + header_value

    def _parse_header(self, header: str) -> dict:
        result = {}
        for item in header[7:].split(","):
            key, value = item.strip().split("=")
            value = value[1:-1] if value[0] == value[-1] == '"' else value
            result[key] = value

        return result

    def _get_parsed_path(self, url: URL) -> bytes:
        path = url.path or "/"
        if url.query:
            path += "?" + url.query
        return path.encode("utf-8")
