import typing

from .decoders import IdentityDecoder
from .exceptions import ResponseClosed, StreamConsumed


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

    async def stream(self):
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
        async for part in self.body_aiter():
            yield part
        await self.close()

    async def close(self) -> None:
        if not self.is_closed:
            self.is_closed = True
            if self.on_close is not None:
                await self.on_close()
