"""
The `Reader` and `Writer` classes here provide a lightweight layer over
`asyncio.StreamReader` and `asyncio.StreamWriter`.

Similarly `PoolSemaphore` is a lightweight layer over `BoundedSemaphore`.

These classes help encapsulate the timeout logic, make it easier to unit-test
protocols, and help keep the rest of the package more `async`/`await`
based, and less strictly `asyncio`-specific.
"""
import asyncio
import ssl
import typing

from .config import DEFAULT_TIMEOUT_CONFIG, PoolLimits, TimeoutConfig
from .exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from .interfaces import (
    BasePoolSemaphore,
    BaseReader,
    BaseWriter,
    ConcurrencyBackend,
    Protocol,
)

OptionalTimeout = typing.Optional[TimeoutConfig]


SSL_MONKEY_PATCH_APPLIED = False


def ssl_monkey_patch() -> None:
    """
    Monky-patch for https://bugs.python.org/issue36709

    This prevents console errors when outstanding HTTPS connections
    still exist at the point of exiting.

    Clients which have been opened using a `with` block, or which have
    had `close()` closed, will not exhibit this issue in the first place.
    """
    MonkeyPatch = asyncio.selector_events._SelectorSocketTransport  # type: ignore

    _write = MonkeyPatch.write

    def _fixed_write(self, data: bytes) -> None:  # type: ignore
        if not self._loop.is_closed():
            _write(self, data)

    MonkeyPatch.write = _fixed_write


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
        self.stream_writer.write(data)  # pragma: nocover

    async def write(self, data: bytes, timeout: OptionalTimeout = None) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        self.stream_writer.write(data)
        try:
            await asyncio.wait_for(  # type: ignore
                self.stream_writer.drain(), timeout.write_timeout
            )
        except asyncio.TimeoutError:
            raise WriteTimeout()

    async def close(self) -> None:
        self.stream_writer.close()


class PoolSemaphore(BasePoolSemaphore):
    def __init__(self, pool_limits: PoolLimits):
        self.pool_limits = pool_limits

    @property
    def semaphore(self) -> typing.Optional[asyncio.BoundedSemaphore]:
        if not hasattr(self, "_semaphore"):
            max_connections = self.pool_limits.hard_limit
            if max_connections is None:
                self._semaphore = None
            else:
                self._semaphore = asyncio.BoundedSemaphore(value=max_connections)
        return self._semaphore

    async def acquire(self) -> None:
        if self.semaphore is None:
            return

        timeout = self.pool_limits.pool_timeout
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout)
        except asyncio.TimeoutError:
            raise PoolTimeout()

    def release(self) -> None:
        if self.semaphore is None:
            return

        self.semaphore.release()


class AsyncioBackend(ConcurrencyBackend):
    def __init__(self) -> None:
        global SSL_MONKEY_PATCH_APPLIED

        if not SSL_MONKEY_PATCH_APPLIED:
            ssl_monkey_patch()
        SSL_MONKEY_PATCH_APPLIED = True

    async def connect(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> typing.Tuple[BaseReader, BaseWriter, Protocol]:
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

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)
