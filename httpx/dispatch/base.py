import typing
from types import TracebackType

from ..config import Timeout
from ..models import (
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    URLTypes,
)


class SyncDispatcher:
    """
    Base class for Dispatcher classes, that handle sending the request.
    """

    def send(self, request: Request, timeout: Timeout = None) -> Response:
        raise NotImplementedError()  # pragma: nocover

    def close(self) -> None:
        pass  # pragma: nocover


class AsyncDispatcher:
    """
    Base class for AsyncDispatcher classes, that handle sending the request.

    Stubs out the interface, as well as providing a `.request()` convenience
    implementation, to make it easy to use or test stand-alone AsyncDispatchers,
    without requiring a complete `AsyncClient` instance.
    """

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        timeout: Timeout = None,
    ) -> Response:
        request = Request(method, url, data=data, params=params, headers=headers)
        return await self.send(request, timeout=timeout)

    async def send(self, request: Request, timeout: Timeout = None) -> Response:
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
