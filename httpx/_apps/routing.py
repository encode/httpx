import re
import typing

from httpx._exceptions import UnsupportedProtocol
from httpx._models import Request, Response
from httpx._transports.base import (
    AsyncBaseTransport,
    AsyncByteStream,
    BaseTransport,
    SyncByteStream,
)

PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)}")


class Route:
    def __init__(self, path: str, endpoint: typing.Callable) -> None:
        self.path = path
        self.endpoint = endpoint
        self.regex = self._compile_regex(path)

    def _compile_regex(self, path: str) -> re.Pattern:
        regex = "^"
        idx = 0

        for match in PARAM_REGEX.finditer(path):
            (param_name,) = match.groups()
            regex += re.escape(path[idx : match.start()])
            regex += f"(?P<{param_name}>[^/]+)"
            idx = match.end()

        regex += re.escape(path[idx:]) + "$"
        return re.compile(regex)

    def matches(self, request: Request) -> bool:
        match = self.regex.match(request.url.path)
        return bool(match)

    def handle(self, request: Request) -> Response:
        return self.endpoint(request)


class Router(BaseTransport, AsyncBaseTransport):
    def __init__(self, routes: typing.List[Route]):
        self.routes = routes

    def handle_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: SyncByteStream,
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], SyncByteStream, dict
    ]:
        request = Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        request.read()
        if request.url.scheme not in ("http", "https"):
            raise UnsupportedProtocol(f"Scheme {request.url.scheme!r} not supported.")
        response = self.handle(request)
        assert isinstance(response.stream, SyncByteStream)
        return (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.extensions,
        )

    async def handle_async_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: AsyncByteStream,
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], AsyncByteStream, dict
    ]:
        request = Request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
        )
        await request.aread()
        if request.url.scheme not in ("http", "https"):
            raise UnsupportedProtocol(f"Scheme {request.url.scheme!r} not supported.")
        response = self.handle(request)
        assert isinstance(response.stream, AsyncByteStream)
        return (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.extensions,
        )

    def handle(self, request: Request) -> Response:
        for route in self.routes:
            if route.matches(request):
                return route.handle(request)

        return self.handle_not_found(request)

    def handle_not_found(self, request: Request) -> Response:
        return Response(404, text="Not found")
