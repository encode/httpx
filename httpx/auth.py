import hashlib
import os
import re
import time
import typing
from base64 import b64encode
from urllib.request import parse_http_list

from .exceptions import ProtocolError, RequestBodyUnavailable
from .models import Request, Response
from .utils import to_bytes, to_str, unquote

AuthTypes = typing.Union[
    typing.Tuple[typing.Union[str, bytes], typing.Union[str, bytes]],
    typing.Callable[["Request"], "Request"],
    "Auth",
]


class Auth:
    """
    Base class for all authentication schemes.
    """

    requires_request_body = False

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        """
        Execute the authentication flow.

        To dispatch a request, `yield` it:

        ```
        yield request
        ```

        The client will `.send()` the response back into the flow generator. You can
        access it like so:

        ```
        response = yield request
        ```

        A `return` (or reaching the end of the generator) will result in the
        client returning the last response obtained from the server.

        You can dispatch as many requests as is necessary.
        """
        yield request


class FunctionAuth(Auth):
    """
    Allows the 'auth' argument to be passed as a simple callable function,
    that takes the request, and returns a new, modified request.
    """

    def __init__(self, func: typing.Callable[[Request], Request]) -> None:
        self.func = func

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        yield self.func(request)


class BasicAuth(Auth):
    """
    Allows the 'auth' argument to be passed as a (username, password) pair,
    and uses HTTP Basic authentication.
    """

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        self.auth_header = self.build_auth_header(username, password)

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        request.headers["Authorization"] = self.auth_header
        yield request

    def build_auth_header(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> str:
        userpass = b":".join((to_bytes(username), to_bytes(password)))
        token = b64encode(userpass).decode().strip()
        return f"Basic {token}"


class DigestAuth(Auth):
    ALGORITHM_TO_HASH_FUNCTION: typing.Dict[str, typing.Callable] = {
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
        self.username = to_bytes(username)
        self.password = to_bytes(password)

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        if not request.stream.can_replay():
            raise RequestBodyUnavailable("Request body is no longer available.")
        response = yield request

        if response.status_code != 401 or "www-authenticate" not in response.headers:
            # If the response is not a 401 WWW-Authenticate, then we don't
            # need to build an authenticated request.
            return

        header = response.headers["www-authenticate"]
        try:
            challenge = DigestAuthChallenge.from_header(header)
        except ValueError:
            raise ProtocolError("Malformed Digest authentication header")

        request.headers["Authorization"] = self._build_auth_header(request, challenge)
        yield request

    def _build_auth_header(
        self, request: Request, challenge: "DigestAuthChallenge"
    ) -> str:
        hash_func = self.ALGORITHM_TO_HASH_FUNCTION[challenge.algorithm]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode()

        A1 = b":".join((self.username, challenge.realm, self.password))

        path = request.url.full_path.encode("utf-8")
        A2 = b":".join((request.method.encode(), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        nonce_count = 1  # TODO: implement nonce counting
        nc_value = b"%08x" % nonce_count
        cnonce = self._get_client_nonce(nonce_count, challenge.nonce)

        HA1 = digest(A1)
        if challenge.algorithm.lower().endswith("-sess"):
            HA1 = digest(b":".join((HA1, challenge.nonce, cnonce)))

        qop = self._resolve_qop(challenge.qop)
        if qop is None:
            digest_data = [HA1, challenge.nonce, HA2]
        else:
            digest_data = [challenge.nonce, nc_value, cnonce, qop, HA2]
        key_digest = b":".join(digest_data)

        format_args = {
            "username": self.username,
            "realm": challenge.realm,
            "nonce": challenge.nonce,
            "uri": path,
            "response": digest(b":".join((HA1, key_digest))),
            "algorithm": challenge.algorithm.encode(),
        }
        if challenge.opaque:
            format_args["opaque"] = challenge.opaque
        if qop:
            format_args["qop"] = b"auth"
            format_args["nc"] = nc_value
            format_args["cnonce"] = cnonce

        return "Digest " + self._get_header_value(format_args)

    def _get_client_nonce(self, nonce_count: int, nonce: bytes) -> bytes:
        s = str(nonce_count).encode()
        s += nonce
        s += time.ctime().encode()
        s += os.urandom(8)

        return hashlib.sha1(s).hexdigest()[:16].encode()

    def _get_header_value(self, header_fields: typing.Dict[str, bytes]) -> str:
        NON_QUOTED_FIELDS = ("algorithm", "qop", "nc")
        QUOTED_TEMPLATE = '{}="{}"'
        NON_QUOTED_TEMPLATE = "{}={}"

        header_value = ""
        for i, (field, value) in enumerate(header_fields.items()):
            if i > 0:
                header_value += ", "
            template = (
                QUOTED_TEMPLATE
                if field not in NON_QUOTED_FIELDS
                else NON_QUOTED_TEMPLATE
            )
            header_value += template.format(field, to_str(value))

        return header_value

    def _resolve_qop(self, qop: typing.Optional[bytes]) -> typing.Optional[bytes]:
        if qop is None:
            return None
        qops = re.split(b", ?", qop)
        if b"auth" in qops:
            return b"auth"

        if qops == [b"auth-int"]:
            raise NotImplementedError("Digest auth-int support is not yet implemented")

        raise ProtocolError(f'Unexpected qop value "{qop!r}" in digest auth')


class DigestAuthChallenge:
    def __init__(
        self,
        realm: bytes,
        nonce: bytes,
        algorithm: str = None,
        opaque: typing.Optional[bytes] = None,
        qop: typing.Optional[bytes] = None,
    ) -> None:
        self.realm = realm
        self.nonce = nonce
        self.algorithm = algorithm or "MD5"
        self.opaque = opaque
        self.qop = qop

    @classmethod
    def from_header(cls, header: str) -> "DigestAuthChallenge":
        """Returns a challenge from a Digest WWW-Authenticate header.
        These take the form of:
        `Digest realm="realm@host.com",qop="auth,auth-int",nonce="abc",opaque="xyz"`
        """
        scheme, _, fields = header.partition(" ")
        if scheme.lower() != "digest":
            raise ValueError("Header does not start with 'Digest'")

        header_dict: typing.Dict[str, str] = {}
        for field in parse_http_list(fields):
            key, value = field.strip().split("=", 1)
            header_dict[key] = unquote(value)

        try:
            return cls.from_header_dict(header_dict)
        except KeyError as exc:
            raise ValueError("Malformed Digest WWW-Authenticate header") from exc

    @classmethod
    def from_header_dict(cls, header_dict: dict) -> "DigestAuthChallenge":
        realm = header_dict["realm"].encode()
        nonce = header_dict["nonce"].encode()
        qop = header_dict["qop"].encode() if "qop" in header_dict else None
        opaque = header_dict["opaque"].encode() if "opaque" in header_dict else None
        algorithm = header_dict.get("algorithm")
        return cls(
            realm=realm, nonce=nonce, qop=qop, opaque=opaque, algorithm=algorithm
        )
