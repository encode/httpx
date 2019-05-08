import typing
from types import TracebackType

from .config import TimeoutConfig
from .models import (
    URL,
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    URLTypes,
)

OptionalTimeout = typing.Optional[TimeoutConfig]


class Adapter:
    """
    The base class for all adapter or dispatcher classes.

    Stubs out the interface, as well as providing a `.request()` convienence
    implementation, to make it easy to use or test stand-alone adapters,
    without requiring a complete `Client` instance.
    """

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        **options: typing.Any,
    ) -> Response:
        request = Request(
            method, url, data=data, query_params=query_params, headers=headers
        )
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
    """
    A stream reader. Abstracts away any asyncio-specfic interfaces
    into a more generic base class, that we can use with alternate
    backend, or for stand-alone test cases.
    """

    async def read(self, n: int, timeout: OptionalTimeout = None) -> bytes:
        raise NotImplementedError()  # pragma: no cover


class BaseWriter:
    """
    A stream writer. Abstracts away any asyncio-specfic interfaces
    into a more generic base class, that we can use with alternate
    backend, or for stand-alone test cases.
    """

    def write_no_block(self, data: bytes) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def write(self, data: bytes, timeout: OptionalTimeout = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class BasePoolSemaphore:
    """
    A semaphore for use with connection pooling.

    Abstracts away any asyncio-specfic interfaces.
    """

    async def acquire(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def release(self) -> None:
        raise NotImplementedError()  # pragma: no cover
