import types
import typing

from ._content import Content
from ._streams import ByteStream, Stream
from ._headers import Headers
from ._urls import URL

__all__ = ["Request"]


class Request:
    def __init__(
        self,
        method: str,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ):
        self.method = method
        self.url = URL(url)
        self.headers = Headers(headers)
        self.stream: Stream = ByteStream(b"")

        # https://datatracker.ietf.org/doc/html/rfc2616#section-14.23
        # RFC 2616, Section 14.23, Host.
        #
        # A client MUST include a Host header field in all HTTP/1.1 request messages.
        if "Host" not in self.headers:
            self.headers = self.headers.copy_set("Host", self.url.netloc)

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
            # The presence of a message-body in a request is signaled by the
            # inclusion of a Content-Length or Transfer-Encoding header field in
            # the request's message-headers.
            content_length: int | None = self.stream.size
            if content_length is None:
                self.headers = self.headers.copy_set("Transfer-Encoding", "chunked")
            elif content_length > 0:
                self.headers = self.headers.copy_set("Content-Length", str(content_length))

        elif method in ("POST", "PUT", "PATCH"):
            # https://datatracker.ietf.org/doc/html/rfc7230#section-3.3.2
            # RFC 7230, Section 3.3.2, Content Length.
            #
            # A user agent SHOULD send a Content-Length in a request message when no
            # Transfer-Encoding is sent and the request method defines a meaning for
            # an enclosed payload body. For example, a Content-Length header field is
            # normally sent in a POST request even when the value is 0.
            # (indicating an empty payload body).
            self.headers = self.headers.copy_set("Content-Length", "0")

    @property
    def body(self) -> bytes:
        if not hasattr(self, '_body'):
            raise RuntimeError("'.body' cannot be accessed without calling '.read()'")
        return self._body

    async def read(self) -> bytes:
        if not hasattr(self, '_body'):
            self._body = await self.stream.read()
            self.stream = ByteStream(self._body)
        return self._body

    async def close(self) -> None:
        await self.stream.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None
    ):
        await self.close()

    def __repr__(self):
        return f"<Request [{self.method} {str(self.url)!r}]>"
