import hashlib
import typing
import time
import os
from base64 import b64encode
from urllib.parse import urlparse

from .models import AsyncRequest, AsyncResponse


class AuthBase:
    """
    Base class that all auth implementations derive from.
    """

    def __call__(self, request: AsyncRequest) -> AsyncRequest:
        raise NotImplementedError("Auth hooks must be callable.")  # pragma: nocover


class HTTPBasicAuth(AuthBase):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self.username = username
        self.password = password

    def __call__(self, request: AsyncRequest) -> AsyncRequest:
        request.headers["Authorization"] = self.build_auth_header()
        return request

    def build_auth_header(self) -> str:
        username, password = self.username, self.password

        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()
        return f"Basic {token}"


class HTTPDigestAuth:

    ALGORITHM_TO_HASH_FUNCTION = {
        "MD5": hashlib.md5,
        "SHA": hashlib.sha1,
        "SHA-256": hashlib.sha256,
        "SHA-512": hashlib.sha512,
    }

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self.username = username
        self.password = password

    def __call__(self, request: AsyncRequest, response) -> AsyncRequest:
        auth_header = self.build_auth_header(request, response)
        if auth_header is not None:
            # TODO: raise instead of returning None?
            request.headers["Authorization"] = auth_header
        return request

    def build_auth_header(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> typing.Optional[str]:
        # Retrieve challenge from response header
        header = response.headers.get("www-authenticate")
        assert header.lower().startswith("digest")
        challenge = self._parse_header(header)
        algorithm = challenge.get("algorithm", "MD5")

        realm = _safe_encode(challenge["realm"])
        nonce = _safe_encode(challenge["nonce"])
        qop = _safe_encode(challenge["qop"]) if "qop" in challenge else None
        opaque = _safe_encode(challenge["opaque"]) if "opaque" in challenge else None
        username = _safe_encode(self.username)
        password = _safe_encode(self.password)

        # Assemble parts depending on hash algorithms
        hash_func = self.ALGORITHM_TO_HASH_FUNCTION[
            algorithm.replace("-SESS", "").upper()
        ]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode("utf-8")

        def keyed_digest(secret, data) -> bytes:
            return digest(b":".join((secret, data)))

        A1 = b":".join((username, realm, password))
        HA1 = digest(A1)

        path = self._get_parsed_path(request.url)
        A2 = b":".join((request.method.encode("utf-8"), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        # Construct Authenticate header string
        nonce_count = 1  # TODO: use contextvars to count properly
        nc_value = b"%08x" % nonce_count

        s = str(nonce_count).encode("utf-8")
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

    def _parse_header(self, header):
        result = {}
        for item in header[7:].split(","):
            key, value = item.strip().split("=")
            value = value[1:-1] if value[0] == value[-1] == '"' else value
            result[key] = value

        return result

    def _get_parsed_path(self, url):
        path = url.path or "/"
        if url.query:
            path += "?" + url.query
        return path.encode("utf-8")


def _safe_encode(str_or_bytes) -> bytes:
    return (
        str_or_bytes.encode("utf-8") if isinstance(str_or_bytes, str) else str_or_bytes
    )

