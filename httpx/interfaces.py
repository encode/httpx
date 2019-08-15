import enum
import ssl
import typing
from types import TracebackType

from .config import CertTypes, PoolLimits, TimeoutConfig, TimeoutTypes, VerifyTypes
from .models import (
    AsyncRequest,
    AsyncRequestData,
    AsyncResponse,
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    URLTypes,
)


class Protocol(str, enum.Enum):
    HTTP_11 = "HTTP/1.1"
    HTTP_2 = "HTTP/2"


class AsyncDispatcher:
    """
    Base class for async dispatcher classes, that handle sending the request.

    Stubs out the interface, as well as providing a `.request()` convenience
    implementation, to make it easy to use or test stand-alone dispatchers,
    without requiring a complete `Client` instance.
    """

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: AsyncRequestData = b"",
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        request = AsyncRequest(method, url, data=data, params=params, headers=headers)
        return await self.send(request, verify=verify, cert=cert, timeout=timeout)

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        raise NotImplementedError()  # pragma: nocover

    async def close(self) -> None:
        pass  # pragma: nocover

    async def __aenter__(self) -> "AsyncDispatcher":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()


class Dispatcher:
    """
    Base class for synchronous dispatcher classes, that handle sending the request.

    Stubs out the interface, as well as providing a `.request()` convenience
    implementation, to make it easy to use or test stand-alone dispatchers,
    without requiring a complete `Client` instance.
    """

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        request = Request(method, url, data=data, params=params, headers=headers)
        return self.send(request, verify=verify, cert=cert, timeout=timeout)

    def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        raise NotImplementedError()  # pragma: nocover

    def close(self) -> None:
        pass  # pragma: nocover

    def __enter__(self) -> "Dispatcher":
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()


class BaseReader:
    """
    A stream reader. Abstracts away any asyncio-specfic interfaces
    into a more generic base class, that we can use with alternate
    backend, or for stand-alone test cases.
    """

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: typing.Any = None
    ) -> bytes:
        raise NotImplementedError()  # pragma: no cover

    def is_connection_dropped(self) -> bool:
        raise NotImplementedError()  # pragma: no cover


class BaseWriter:
    """
    A stream writer. Abstracts away any asyncio-specific interfaces
    into a more generic base class, that we can use with alternate
    backend, or for stand-alone test cases.
    """

    def write_no_block(self, data: bytes) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def write(self, data: bytes, timeout: TimeoutConfig = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class BaseEvent:
    def set(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def is_set(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    async def wait(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class BasePoolSemaphore:
    """
    A semaphore for use with connection pooling.

    Abstracts away any asyncio-specific interfaces.
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

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    async def iterate_in_threadpool(self, iterator):  # type: ignore
        class IterationComplete(Exception):
            pass

        def next_wrapper(iterator):  # type: ignore
            try:
                return next(iterator)
            except StopIteration:
                raise IterationComplete()

        while True:
            try:
                yield await self.run_in_threadpool(next_wrapper, iterator)
            except IterationComplete:
                break

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        raise NotImplementedError()  # pragma: no cover

    def create_event(self) -> BaseEvent:
        raise NotImplementedError()  # pragma: no cover

    def iterate(self, async_iterator):  # type: ignore
        while True:
            try:
                yield self.run(async_iterator.__anext__)
            except StopAsyncIteration:
                break

    def background_manager(self) -> "BaseBackgroundManager":
        raise NotImplementedError()  # pragma: no cover

    def body_iterator(self) -> "BaseBodyIterator":
        raise NotImplementedError()  # pragma: no cover


class BaseBodyIterator:
    """
    Provides a byte-iterator interface that the client can use to
    ingest the response content from.
    """

    def iterate(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator, used by the client to consume the response body.
        """
        raise NotImplementedError()  # pragma: no cover

    async def drain(self) -> None:
        """
        Drain any remaining body, in order to allow any blocked `put()` calls
        to complete.
        """
        async for chunk in self.iterate():
            pass  # pragma: no cover

    async def put(self, data: bytes) -> None:
        """
        Used by the server to add data to the response body.
        """
        raise NotImplementedError()  # pragma: no cover

    async def done(self) -> None:
        """
        Used by the server to signal the end of the response body.
        """
        raise NotImplementedError()  # pragma: no cover


class BaseBackgroundManager:
    def start_soon(self, coroutine: typing.Callable, *args: typing.Any) -> None:
        raise NotImplementedError()  # pragma: no cover

    def will_wait_for_first_completed(self) -> typing.AsyncContextManager:
        raise NotImplementedError()  # pragma: no cover

    async def __aenter__(self) -> "BaseBackgroundManager":
        raise NotImplementedError()  # pragma: no cover

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        await self.__aexit__(None, None, None)
