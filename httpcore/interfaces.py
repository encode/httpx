import enum
import ssl
import typing
from types import TracebackType

from .config import PoolLimits, SSLConfig, TimeoutConfig
from .models import (
    URL,
    Headers,
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    URLTypes,
)

OptionalTimeout = typing.Optional[TimeoutConfig]


class Protocol(str, enum.Enum):
    HTTP_11 = "HTTP/1.1"
    HTTP_2 = "HTTP/2"


class Dispatcher:
    """
    Base class for dispatcher classes, that handle sending the request.

    Stubs out the interface, as well as providing a `.request()` convienence
    implementation, to make it easy to use or test stand-alone dispatchers,
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
        stream: bool = False,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None
    ) -> Response:
        request = Request(
            method, url, data=data, query_params=query_params, headers=headers
        )
        self.prepare_request(request)
        response = await self.send(request, stream=stream, ssl=ssl, timeout=timeout)
        return response

    def prepare_request(self, request: Request) -> None:
        request.prepare()

    async def send(
        self,
        request: Request,
        stream: bool = False,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        raise NotImplementedError()  # pragma: nocover

    async def close(self) -> None:
        pass  # pragma: nocover

    async def __aenter__(self) -> "Dispatcher":
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


class ConcurrencyBackend:
    async def connect(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> typing.Tuple[BaseReader, BaseWriter, Protocol]:
        raise NotImplementedError()  # pragma: no cover

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        raise NotImplementedError()  # pragma: no cover
