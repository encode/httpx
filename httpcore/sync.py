import typing
from types import TracebackType

from .compat import asyncio_run
from .config import SSLConfig, TimeoutConfig
from .datastructures import URL, Client, Response
from .pool import ConnectionPool


class SyncResponse:
    def __init__(self, response: Response):
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def reason(self) -> str:
        return self._response.reason

    @property
    def headers(self) -> typing.List[typing.Tuple[bytes, bytes]]:
        return self._response.headers

    @property
    def body(self) -> bytes:
        return self._response.body

    def read(self) -> bytes:
        return asyncio_run(self._response.read())

    def stream(self) -> typing.Iterator[bytes]:
        inner = self._response.stream()
        while True:
            try:
                yield asyncio_run(inner.__anext__())
            except StopAsyncIteration as exc:
                break

    def close(self) -> None:
        return asyncio_run(self._response.close())


class SyncClient:
    def __init__(self, client: Client):
        self._client = client

    def request(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
        stream: bool = False,
    ) -> SyncResponse:
        response = asyncio_run(
            self._client.request(
                method,
                url,
                headers=headers,
                body=body,
                ssl=ssl,
                timeout=timeout,
                stream=stream,
            )
        )
        return SyncResponse(response)

    def close(self) -> None:
        asyncio_run(self._client.close())

    def __enter__(self) -> "SyncClient":
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()


def SyncConnectionPool(*args: typing.Any, **kwargs: typing.Any) -> SyncClient:
    client = ConnectionPool(*args, **kwargs)  # type: ignore
    return SyncClient(client)
