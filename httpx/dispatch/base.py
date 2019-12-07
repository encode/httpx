import typing
from types import TracebackType

from ..config import CertTypes, Timeout, VerifyTypes
from ..models import (
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    URLTypes,
)


class Dispatcher:
    """
    Base class for dispatcher classes, that handle sending the request.

    Stubs out the interface, as well as providing a `.request()` convenience
    implementation, to make it easy to use or test stand-alone dispatchers,
    without requiring a complete `Client` instance.
    """

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: Timeout = None,
    ) -> Response:
        request = Request(method, url, data=data, params=params, headers=headers)
        return await self.send(request, verify=verify, cert=cert, timeout=timeout)

    async def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: Timeout = None,
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


class OpenConnection:
    """
    Base class for connection classes that interact with a host via HTTP.
    """

    @property
    def is_http2(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    async def send(self, request: Request, timeout: Timeout = None,) -> Response:
        raise NotImplementedError()  # pragma: no cover

    @property
    def is_closed(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def is_connection_dropped(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover
