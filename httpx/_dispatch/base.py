from types import TracebackType
from typing import List, Tuple, Type

from .._config import Timeout
from .._content_streams import ContentStream
from .._models import (
    URL,
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

    def send(
        self,
        method: bytes,
        url: URL,
        headers: List[Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: Timeout = None,
    ) -> Tuple[int, str, List[Tuple[bytes, bytes]], ContentStream]:
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
        request = Request(
            method=method, url=url, data=data, params=params, headers=headers
        )
        status_code, http_version, headers, stream = await self.send(
            request.method.encode(),
            request.url,
            request.headers.raw,
            request.stream,
            timeout=timeout,
        )
        return Response(
            status_code,
            http_version=http_version,
            headers=headers,
            stream=stream,
            request=request,
        )

    async def send(
        self,
        method: bytes,
        url: URL,
        headers: List[Tuple[bytes, bytes]],
        stream: ContentStream,
        timeout: Timeout = None,
    ) -> Tuple[int, str, List[Tuple[bytes, bytes]], ContentStream]:
        raise NotImplementedError()  # pragma: nocover

    async def close(self) -> None:
        pass  # pragma: nocover

    async def __aenter__(self) -> "AsyncDispatcher":
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()
