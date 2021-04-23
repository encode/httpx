import typing
from urllib.parse import quote

from httpx._apps.routing import Route, Router
from httpx._status_codes import codes
from httpx._transports.base import BaseTransport, SyncByteStream


class WSGIStream(SyncByteStream):
    def __init__(self, wsgi_input: typing.Iterable[bytes]) -> None:
        self._wsgi_input = wsgi_input

    def __iter__(self) -> typing.Iterator[bytes]:
        for chunk in self._wsgi_input:
            yield chunk


class WSGIApp(BaseTransport):
    def __init__(self, routes: typing.List[Route]) -> None:
        self.router = Router(routes)

    def __call__(
        self, environ: dict, start_response: typing.Callable
    ) -> typing.Iterable[bytes]:
        method = environ["REQUEST_METHOD"].encode("ascii")
        scheme = environ["wsgi.url_scheme"].encode("ascii")
        host = environ.get("HTTP_HOST", environ["SERVER_NAME"]).encode("ascii")
        port = environ["SERVER_PORT"]
        path = quote(environ.get("SCRIPT_NAME", "")).encode("ascii")
        path += quote(environ.get("PATH_INFO", "")).encode("ascii")
        if environ.get("QUERY_STRING"):
            path += b"?" + environ["QUERY_STRING"].encode("ascii")
        url = (scheme, host, port, path)
        headers = [
            (key.encode("ascii"), value.encode("ascii"))
            for key, value in environ.items()
            if key in ("CONTENT_TYPE", "CONTENT_LENGTH")
        ]
        headers += [
            (key[5:].encode("ascii"), value.encode("ascii"))
            for key, value in environ.items()
            if key.startswith("HTTP_")
        ]
        stream: SyncByteStream = WSGIStream(environ["wsgi.input"])
        extensions: dict = {}

        status_code, headers, stream, extensions = self.handle_request(
            method=method,
            url=url,
            headers=headers,
            stream=stream,
            extensions=extensions,
        )

        reason_phrase = codes.get_reason_phrase(status_code)
        wsgi_status = f"{status_code} {reason_phrase}"
        wsgi_headers = [
            (key.decode("ascii"), value.decode("ascii")) for key, value in headers
        ]

        start_response(wsgi_status, wsgi_headers, exc_info=None)

        return stream

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
        return self.router.handle_request(method, url, headers, stream, extensions)
