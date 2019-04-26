import typing
from types import TracebackType

from .models import URL, Request, Response


class Adapter:
    async def request(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        headers: typing.List[typing.Tuple[bytes, bytes]] = [],
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        **options: typing.Any,
    ) -> Response:
        request = Request(method, url, headers=headers, body=body)
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
