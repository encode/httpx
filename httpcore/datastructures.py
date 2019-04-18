import http
import typing
from urllib.parse import urlsplit

from .decoders import (
    ACCEPT_ENCODING,
    SUPPORTED_DECODERS,
    Decoder,
    IdentityDecoder,
    MultiDecoder,
)
from .exceptions import ResponseClosed, StreamConsumed


class URL:
    def __init__(self, url: str = "") -> None:
        self.components = urlsplit(url)
        if not self.components.scheme:
            raise ValueError("No scheme included in URL.")
        if self.components.scheme not in ("http", "https"):
            raise ValueError('URL scheme must be "http" or "https".')
        if not self.components.hostname:
            raise ValueError("No hostname included in URL.")

    @property
    def scheme(self) -> str:
        return self.components.scheme

    @property
    def netloc(self) -> str:
        return self.components.netloc

    @property
    def path(self) -> str:
        return self.components.path

    @property
    def query(self) -> str:
        return self.components.query

    @property
    def hostname(self) -> str:
        return self.components.hostname

    @property
    def port(self) -> int:
        port = self.components.port
        if port is None:
            return {"https": 443, "http": 80}[self.scheme]
        return port

    @property
    def target(self) -> str:
        path = self.path or "/"
        query = self.query
        if query:
            return path + "?" + query
        return path

    @property
    def is_secure(self) -> bool:
        return self.components.scheme == "https"


class Request:
    def __init__(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
    ):
        self.method = method
        self.url = URL(url) if isinstance(url, str) else url
        self.headers = list(headers)
        if isinstance(body, bytes):
            self.is_streaming = False
            self.body = body
        else:
            self.is_streaming = True
            self.body_aiter = body
        self.headers = self._auto_headers() + self.headers

    def _auto_headers(self) -> typing.List[typing.Tuple[bytes, bytes]]:
        has_host = False
        has_content_length = False
        has_accept_encoding = False

        for header, value in self.headers:
            header = header.strip().lower()
            if header == b"host":
                has_host = True
            elif header in (b"content-length", b"transfer-encoding"):
                has_content_length = True
            elif header == b"accept-encoding":
                has_accept_encoding = True

        headers = []  # type: typing.List[typing.Tuple[bytes, bytes]]

        if not has_host:
            headers.append((b"host", self.url.netloc.encode("ascii")))
        if not has_content_length:
            if self.is_streaming:
                headers.append((b"transfer-encoding", b"chunked"))
            elif self.body:
                content_length = str(len(self.body)).encode()
                headers.append((b"content-length", content_length))
        if not has_accept_encoding:
            headers.append((b"accept-encoding", ACCEPT_ENCODING))

        return headers

    async def stream(self) -> typing.AsyncIterator[bytes]:
        assert self.is_streaming

        async for part in self.body_aiter:
            yield part


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        reason: typing.Optional[str] = None,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        on_close: typing.Callable = None,
    ):
        self.status_code = status_code
        if not reason:
            try:
                self.reason = http.HTTPStatus(status_code).phrase
            except ValueError as exc:
                self.reason = ""
        else:
            self.reason = reason
        self.headers = list(headers)
        self.on_close = on_close
        self.is_closed = False
        self.is_streamed = False

        decoders = []  # type: typing.List[Decoder]
        for header, value in self.headers:
            if header.strip().lower() == b"content-encoding":
                for part in value.split(b","):
                    part = part.strip().lower()
                    decoder_cls = SUPPORTED_DECODERS[part]
                    decoders.append(decoder_cls())

        if len(decoders) == 0:
            self.decoder = IdentityDecoder()  # type: Decoder
        elif len(decoders) == 1:
            self.decoder = decoders[0]
        else:
            self.decoder = MultiDecoder(decoders)

        if isinstance(body, bytes):
            self.is_closed = True
            self.body = self.decoder.decode(body) + self.decoder.flush()
        else:
            self.body_aiter = body

    async def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "body"):
            body = b""
            async for part in self.stream():
                body += part
            self.body = body
        return self.body

    async def stream(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, and brotli encoded responses.
        """
        if hasattr(self, "body"):
            yield self.body
        else:
            async for chunk in self.raw():
                yield self.decoder.decode(chunk)
            yield self.decoder.flush()

    async def raw(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if self.is_streamed:
            raise StreamConsumed()
        if self.is_closed:
            raise ResponseClosed()
        self.is_streamed = True
        async for part in self.body_aiter:
            yield part
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.
        Automatically called if the response body is read to completion.
        """
        if not self.is_closed:
            self.is_closed = True
            if self.on_close is not None:
                await self.on_close()
