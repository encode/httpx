from types import TracebackType
from typing import Any, AsyncIterator, Iterator, List, Optional, Tuple, Type, Union


class AsyncByteStream:
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b""  # pragma: nocover

    async def aclose(self) -> None:
        pass  # pragma: nocover

    async def aread(self) -> bytes:
        return b"".join([part async for part in self])


class ByteStream:
    def __iter__(self) -> Iterator[bytes]:
        yield b""  # pragma: nocover

    def close(self) -> None:
        pass  # pragma: nocover

    def read(self) -> bytes:
        return b"".join([part for part in self])


class EmptyByteStream(ByteStream, AsyncByteStream):
    pass


class Origin:
    def __init__(self, scheme: bytes, host: bytes, port: int) -> None:
        self.scheme = scheme
        self.host = host
        self.port = port

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Origin)
            and self.scheme == other.scheme
            and self.host == other.host
            and self.port == other.port
        )

    def __str__(self) -> str:
        scheme = self.scheme.decode("ascii")
        host = self.host.decode("ascii")
        port = str(self.port)
        return f"{scheme}://{host}:{port}"


class RawURL:
    def __init__(
        self, scheme: bytes, host: bytes, port: Optional[int], target: bytes
    ) -> None:
        self.scheme = scheme
        self.host = host
        self.port = port
        self.target = target

    @property
    def origin(self) -> Origin:
        default_port = {b"http": 80, b"https": 443}[self.scheme]
        return Origin(self.scheme, self.host, self.port or default_port)

    def __str__(self) -> str:
        scheme = self.scheme.decode("ascii")
        host = self.host.decode("ascii")
        port_str = "f:{self.port}" if self.port else ""
        target = self.target.decode("ascii")
        return f"{scheme}://{host}{port_str}{target}"


class RawRequest:
    def __init__(
        self,
        method: bytes,
        url: RawURL,
        headers: List[Tuple[bytes, bytes]],
        stream: Union[ByteStream, AsyncByteStream] = None,
        extensions: dict = None,
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.stream = EmptyByteStream() if stream is None else stream
        self.extensions = {} if extensions is None else extensions

    @property
    def sync_stream(self) -> ByteStream:
        assert isinstance(self.stream, ByteStream)
        return self.stream

    @property
    def async_stream(self) -> AsyncByteStream:
        assert isinstance(self.stream, AsyncByteStream)
        return self.stream


class RawResponse:
    def __init__(
        self,
        status: int,
        headers: List[Tuple[bytes, bytes]],
        stream: Union[ByteStream, AsyncByteStream] = None,
        extensions: dict = None,
    ) -> None:
        self.status = status
        self.headers = headers
        self.stream = EmptyByteStream() if stream is None else stream
        self.extensions = {} if extensions is None else extensions

    @property
    def sync_stream(self) -> ByteStream:
        assert isinstance(self.stream, ByteStream)
        return self.stream

    @property
    def async_stream(self) -> AsyncByteStream:
        assert isinstance(self.stream, AsyncByteStream)
        return self.stream

    def __enter__(self) -> "RawResponse":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self.sync_stream.close()

    async def __aenter__(self) -> "RawResponse":
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self.async_stream.aclose()


class ConnectionNotAvailable(Exception):
    pass
