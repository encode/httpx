import typing
from urllib.parse import urlsplit

from .decoders import IdentityDecoder
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
        url: URL,
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
    ):
        self.method = method
        self.url = url
        self.headers = list(headers)
        if isinstance(body, bytes):
            self.is_streaming = False
            self.body = body
        else:
            self.is_streaming = True
            self.body_aiter = body

    async def stream(self) -> typing.AsyncIterator[bytes]:
        assert self.is_streaming

        async for part in self.body_aiter:
            yield part


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        on_close: typing.Callable = None,
    ):
        self.status_code = status_code
        self.headers = list(headers)
        self.on_close = on_close
        self.is_closed = False
        self.is_streamed = False
        self.decoder = IdentityDecoder()
        if isinstance(body, bytes):
            self.is_closed = True
            self.body = body
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
        This will allow us to handle gzip, deflate, and brotli encoded responses.
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
        if not self.is_closed:
            self.is_closed = True
            if self.on_close is not None:
                await self.on_close()
