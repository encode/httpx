"""
The `Reader` and `Writer` classes here provide a lightweight layer over
`asyncio.StreamReader` and `asyncio.StreamWriter`.

They help encapsulate the timeout logic, make it easier to unit-test
protocols, and help keep the rest of the package more `async`/`await`
based, and less strictly `asyncio`-specific.
"""
import asyncio
import enum
import ssl
import typing

from .config import TimeoutConfig, DEFAULT_TIMEOUT_CONFIG
from .exceptions import ConnectTimeout, ReadTimeout, WriteTimeout

OptionalTimeout = typing.Optional[TimeoutConfig]


class Protocol(enum.Enum):
    HTTP_11 = 1
    HTTP_2 = 2


class BaseReader:
    async def read(self, n: int, timeout: OptionalTimeout = None) -> bytes:
        raise NotImplementedError()  # pragma: no cover


class BaseWriter:
    def write_no_block(self, data: bytes) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def write(self, data: bytes, timeout: OptionalTimeout = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class Reader(BaseReader):
    def __init__(
        self, stream_reader: asyncio.StreamReader, timeout: TimeoutConfig
    ) -> None:
        self.stream_reader = stream_reader
        self.timeout = timeout

    async def read(self, n: int, timeout: OptionalTimeout = None) -> bytes:
        if timeout is None:
            timeout = self.timeout

        try:
            data = await asyncio.wait_for(
                self.stream_reader.read(n), timeout.read_timeout
            )
        except asyncio.TimeoutError:
            raise ReadTimeout()

        return data


class Writer(BaseWriter):
    def __init__(self, stream_writer: asyncio.StreamWriter, timeout: TimeoutConfig):
        self.stream_writer = stream_writer
        self.timeout = timeout

    def write_no_block(self, data: bytes) -> None:
        self.stream_writer.write(data)

    async def write(self, data: bytes, timeout: OptionalTimeout = None) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        self.stream_writer.write(data)
        try:
            data = await asyncio.wait_for(  # type: ignore
                self.stream_writer.drain(), timeout.write_timeout
            )
        except asyncio.TimeoutError:
            raise WriteTimeout()

    async def close(self) -> None:
        self.stream_writer.close()


async def connect(
    hostname: str,
    port: int,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
    timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
) -> typing.Tuple[Reader, Writer, Protocol]:
    try:
        stream_reader, stream_writer = await asyncio.wait_for(  # type: ignore
            asyncio.open_connection(hostname, port, ssl=ssl_context),
            timeout.connect_timeout,
        )
    except asyncio.TimeoutError:
        raise ConnectTimeout()

    ssl_object = stream_writer.get_extra_info("ssl_object")
    if ssl_object is None:
        ident = "http/1.1"
    else:
        ident = ssl_object.selected_alpn_protocol()
        if ident is None:
            ident = ssl_object.selected_npn_protocol()

    reader = Reader(stream_reader=stream_reader, timeout=timeout)
    writer = Writer(stream_writer=stream_writer, timeout=timeout)
    protocol = Protocol.HTTP_2 if ident == "h2" else Protocol.HTTP_11

    return (reader, writer, protocol)
