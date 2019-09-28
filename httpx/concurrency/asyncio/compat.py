import asyncio
import ssl
import sys
import typing

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class Stream(Protocol):  # pragma: no cover
    """Protocol defining just the methods we use from asyncio.Stream."""

    def at_eof(self) -> bool:
        ...

    def close(self) -> typing.Awaitable[None]:
        ...

    async def drain(self) -> None:
        ...

    def get_extra_info(self, name: str, default: typing.Any = None) -> typing.Any:
        ...

    async def read(self, n: int = -1) -> bytes:
        ...

    async def start_tls(
        self,
        sslContext: ssl.SSLContext,
        *,
        server_hostname: typing.Optional[str] = None,
        ssl_handshake_timeout: typing.Optional[float] = None,
    ) -> None:
        ...

    def write(self, data: bytes) -> typing.Awaitable[None]:
        ...


async def connect_compat(*args: typing.Any, **kwargs: typing.Any) -> Stream:
    if sys.version_info >= (3, 8):
        return await asyncio.connect(*args, **kwargs)
    else:
        reader, writer = await asyncio.open_connection(*args, **kwargs)
        return StreamCompat(reader, writer)


class StreamCompat:
    """
    Thin wrapper around asyncio.StreamReader/StreamWriter to make them look and
    behave similarly to an asyncio.Stream.
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    def at_eof(self) -> bool:
        return self.reader.at_eof()

    def close(self) -> typing.Awaitable[None]:
        self.writer.close()
        return _OptionalAwait(self.wait_closed)

    async def drain(self) -> None:
        await self.writer.drain()

    def get_extra_info(self, name: str, default: typing.Any = None) -> typing.Any:
        return self.writer.get_extra_info(name, default)

    async def read(self, n: int = -1) -> bytes:
        return await self.reader.read(n)

    async def start_tls(
        self,
        sslContext: ssl.SSLContext,
        *,
        server_hostname: typing.Optional[str] = None,
        ssl_handshake_timeout: typing.Optional[float] = None,
    ) -> None:
        if not sys.version_info >= (3, 7):  # pragma: no cover
            raise NotImplementedError(
                "asyncio.AbstractEventLoop.start_tls() is only available in Python 3.7+"
            )
        else:
            # This code is in an else branch to appease mypy on Python < 3.7

            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            transport = self.writer.transport

            loop = asyncio.get_event_loop()
            loop_start_tls = loop.start_tls  # type: ignore
            tls_transport = await loop_start_tls(
                transport=transport,
                protocol=protocol,
                sslcontext=sslContext,
                server_hostname=server_hostname,
                ssl_handshake_timeout=ssl_handshake_timeout,
            )

            reader.set_transport(tls_transport)
            self.reader = reader
            self.writer = asyncio.StreamWriter(
                transport=tls_transport, protocol=protocol, reader=reader, loop=loop
            )

    def write(self, data: bytes) -> typing.Awaitable[None]:
        self.writer.write(data)
        return _OptionalAwait(self.drain)

    async def wait_closed(self) -> None:
        if sys.version_info >= (3, 7):
            await self.writer.wait_closed()
        # else not much we can do to wait for the connection to close


# This code is copied from cPython 3.8 but with type annotations added:
# https://github.com/python/cpython/blob/v3.8.0b4/Lib/asyncio/streams.py#L1262-L1273
_T = typing.TypeVar("_T")


class _OptionalAwait(typing.Generic[_T]):
    # The class doesn't create a coroutine
    # if not awaited
    # It prevents "coroutine is never awaited" message

    __slots___ = ("_method",)

    def __init__(self, method: typing.Callable[[], typing.Awaitable[_T]]):
        self._method = method

    def __await__(self) -> typing.Generator[typing.Any, None, _T]:
        return self._method().__await__()
