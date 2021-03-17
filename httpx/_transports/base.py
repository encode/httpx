import typing
from types import TracebackType

T = typing.TypeVar("T", bound="BaseTransport")
A = typing.TypeVar("A", bound="AsyncBaseTransport")


class BaseTransport:
    def __enter__(self: T) -> T:
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        pass

    def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: typing.Iterator[bytes] = None,
        ext: dict = None,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], typing.Iterator[bytes], dict
    ]:
        pass

    def close(self) -> None:
        pass


class AsyncBaseTransport:
    async def __aenter__(self: A) -> A:
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        pass

    async def arequest(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: typing.AsyncIterator[bytes] = None,
        ext: dict = None,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], typing.AsyncIterator[bytes], dict
    ]:
        pass

    async def aclose(self) -> None:
        pass
