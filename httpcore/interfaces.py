import typing
from types import TracebackType

from .config import TimeoutConfig
from .models import URL, ByteOrByteStream, HeaderTypes, Request, Response, URLTypes

OptionalTimeout = typing.Optional[TimeoutConfig]


class Adapter:
    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        headers: HeaderTypes = None,
        content: ByteOrByteStream = b"",
        **options: typing.Any,
    ) -> Response:
        request = Request(method, url, headers=headers, content=content)
        self.prepare_request(request)
        response = await self.send(request, **options)
        return response

    def prepare_request(self, request: Request) -> None:
        raise NotImplementedError()  # pragma: nocover

    async def send(self, request: Request, **options: typing.Any) -> Response:
        raise NotImplementedError()  # pragma: nocover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: nocover

    async def __aenter__(self) -> "Adapter":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()


class BaseReader:
    async def read(self, n: int, timeout: OptionalTimeout = None) -> bytes:
        raise NotImplementedError()  # pragma: no cover


class BaseWriter:
    def write_no_block(self, data: bytes) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def write(self, data: bytes, timeout: OptionalTimeout = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class BasePoolSemaphore:
    async def acquire(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def release(self) -> None:
        raise NotImplementedError()  # pragma: no cover
