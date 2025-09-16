import types
import typing

from ._content import Content
from ._streams import ByteStream, Stream
from ._headers import Headers, parse_opts_header

__all__ = ["Response"]

# We're using the same set as stdlib `http.HTTPStatus` here...
#
# https://github.com/python/cpython/blob/main/Lib/http/__init__.py
_codes = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    103: "Early Hints",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Content Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    416: "Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a Teapot",
    421: "Misdirected Request",
    422: "Unprocessable Content",
    423: "Locked",
    424: "Failed Dependency",
    425: "Too Early",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    451: "Unavailable For Legal Reasons",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    510: "Not Extended",
    511: "Network Authentication Required",
}


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ):
        self.status_code = status_code
        self.headers = Headers(headers)
        self.stream: Stream = ByteStream(b"")

        if content is not None:
            if isinstance(content, bytes):
                self.stream = ByteStream(content)
            elif isinstance(content, Stream):
                self.stream = content
            elif isinstance(content, Content):
                ct = content.content_type()
                self.stream = content.encode()
                self.headers = self.headers.copy_set("Content-Type", ct)
            else:
                raise TypeError(f'Expected `Content | Stream | bytes | None` got {type(content)}')

        # https://datatracker.ietf.org/doc/html/rfc2616#section-4.3
        # RFC 2616, Section 4.3, Message Body.
        #
        # All 1xx (informational), 204 (no content), and 304 (not modified) responses
        # MUST NOT include a message-body. All other responses do include a
        # message-body, although it MAY be of zero length.
        if status_code >= 200 and status_code != 204 and status_code != 304:
            content_length: int | None = self.stream.size
            if content_length is None:
                self.headers = self.headers.copy_set("Transfer-Encoding", "chunked")
            else:
                self.headers = self.headers.copy_set("Content-Length", str(content_length))

    @property
    def reason_phrase(self):
        return _codes.get(self.status_code, "Unknown Status Code")

    @property
    def body(self) -> bytes:
        if not hasattr(self, '_body'):
            raise RuntimeError("'.body' cannot be accessed without calling '.read()'")
        return self._body

    @property
    def text(self) -> str:
        if not hasattr(self, '_body'):
            raise RuntimeError("'.text' cannot be accessed without calling '.read()'")
        if not hasattr(self, '_text'):
            ct = self.headers.get('Content-Type', '')
            media, opts = parse_opts_header(ct)
            charset = 'utf-8'
            if media.startswith('text/'):
                charset = opts.get('charset', 'utf-8')
            self._text = self._body.decode(charset)
        return self._text

    def read(self) -> bytes:
        if not hasattr(self, '_body'):
            self._body = self.stream.read()
        return self._body

    def close(self) -> None:
        self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None
    ):
        self.close()

    def __repr__(self):
        return f"<Response [{self.status_code} {self.reason_phrase}]>"
