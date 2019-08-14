import functools
import ssl
import typing
from types import TracebackType

import trio
import trio.abc

from httpx.config import PoolLimits, TimeoutConfig
from httpx.exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from httpx.interfaces import (
    BaseAsyncContextManager,
    BaseBackgroundManager,
    BaseBodyIterator,
    BaseEvent,
    BasePoolSemaphore,
    BaseReader,
    BaseWriter,
    ConcurrencyBackend,
    Protocol,
)
from httpx.concurrency import TimeoutFlag


class Reader(BaseReader):
    def __init__(
        self, receive_stream: trio.abc.ReceiveStream, timeout: TimeoutConfig
    ) -> None:
        self.receive_stream = receive_stream
        self.timeout = timeout
        self.is_eof = False

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> bytes:
        if timeout is None:
            timeout = self.timeout

        while True:
            # Check our flag at the first possible moment, and use a fine
            # grained retry loop if we're not yet in read-timeout mode.
            should_raise = flag is None or flag.raise_on_read_timeout
            read_timeout = timeout.read_timeout if should_raise else 0.01
            with trio.move_on_after(read_timeout) as cancel_scope:
                data = await self.receive_stream.receive_some(max_bytes=n)
            if cancel_scope.cancelled_caught:
                if should_raise:
                    raise ReadTimeout() from None
            else:
                if data == b"":
                    self.is_eof = True
                return data

        return data

    def is_connection_dropped(self) -> bool:
        return self.is_eof


class Writer(BaseWriter):
    def __init__(self, send_stream: trio.abc.SendStream, timeout: TimeoutConfig):
        self.send_stream = send_stream
        self.timeout = timeout

    def write_no_block(self, data: bytes) -> None:
        self.send_stream.send_all(data)  # pragma: nocover

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        while True:
            with trio.move_on_after(timeout.write_timeout) as cancel_scope:
                await self.send_stream.wait_send_all_might_not_block()
                await self.send_stream.send_all(data)
                break
            if cancel_scope.cancelled_caught:
                # We check our flag at the possible moment, in order to
                # allow us to suppress write timeouts, if we've since
                # switched over to read-timeout mode.
                should_raise = flag is None or flag.raise_on_write_timeout
                if should_raise:
                    raise WriteTimeout() from None

    async def close(self) -> None:
        await self.send_stream.aclose()


class PoolSemaphore(BasePoolSemaphore):
    def __init__(self, pool_limits: PoolLimits):
        self.pool_limits = pool_limits

    @property
    def semaphore(self) -> typing.Optional[trio.Semaphore]:
        if not hasattr(self, "_semaphore"):
            max_connections = self.pool_limits.hard_limit
            if max_connections is None:
                self._semaphore = None
            else:
                self._semaphore = trio.Semaphore(
                    initial_value=1, max_value=max_connections
                )
        return self._semaphore

    async def acquire(self) -> None:
        if self.semaphore is None:
            return

        timeout = self.pool_limits.pool_timeout
        with trio.move_on_after(timeout) as cancel_scope:
            await self.semaphore.acquire()
        if cancel_scope.cancelled_caught:
            raise PoolTimeout()

    def release(self) -> None:
        if self.semaphore is None:
            return

        self.semaphore.release()


class TrioBackend(ConcurrencyBackend):
    async def connect(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> typing.Tuple[BaseReader, BaseWriter, Protocol]:
        with trio.move_on_after(timeout.connect_timeout) as cancel_scope:
            if ssl_context is None:
                stream = await trio.open_tcp_stream(hostname, port)
            else:
                stream = await trio.open_ssl_over_tcp_stream(
                    hostname, port, ssl_context=ssl_context
                )
                await stream.do_handshake()
        if cancel_scope.cancelled_caught:
            raise ConnectTimeout()

        if ssl_context is None:
            ident = "http/1.1"  # TODO
        else:
            ident = stream.selected_alpn_protocol()
            if ident is None:
                ident = stream.selected_npn_protocol()

        reader = Reader(receive_stream=stream, timeout=timeout)
        writer = Writer(send_stream=stream, timeout=timeout)
        protocol = Protocol.HTTP_2 if ident == "h2" else Protocol.HTTP_11

        return reader, writer, protocol

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        if kwargs:
            # trio.to_thread.run_async doesn't accept 'kwargs', so bind them in here
            func = functools.partial(func, **kwargs)
        return await trio.to_thread.run_sync(func, *args)

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        if kwargs:
            coroutine = functools.partial(coroutine, **kwargs)
        return trio.run(coroutine, *args)

    async def sleep(self, seconds: float) -> None:
        await trio.sleep(seconds)

    def create_event(self) -> BaseEvent:
        return trio.Event()  # type: ignore

    def background_manager(self) -> "BackgroundManager":
        return BackgroundManager()

    def body_iterator(self) -> "BodyIterator":
        return BodyIterator()


class BackgroundManager(BaseBackgroundManager):
    nursery: trio.Nursery

    def __init__(self) -> None:
        self.nursery_manager = trio.open_nursery()
        self.convert = lambda coroutine: coroutine

    def start_soon(self, coroutine: typing.Callable, *args: typing.Any) -> None:
        self.nursery.start_soon(self.convert(coroutine), *args)

    def will_wait_for_first_completed(self) -> BaseAsyncContextManager:
        return WillWaitForFirstCompleted(self)

    async def __aenter__(self) -> "BackgroundManager":
        self.nursery = await self.nursery_manager.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.nursery_manager.__aexit__(exc_type, exc_value, traceback)


class BodyIterator(BaseBodyIterator):
    def __init__(self) -> None:
        self.send_channel, self.receive_channel = trio.open_memory_channel()

    async def iterate(self) -> typing.AsyncIterator[bytes]:
        async with self.receive_channel:
            async for data in self.receive_channel:
                assert isinstance(data, bytes)
                yield data

    async def put(self, data: bytes) -> None:
        await self.send_channel.send(data)

    async def done(self) -> None:
        await self.send_channel.aclose()


class WillWaitForFirstCompleted(BaseAsyncContextManager):
    nursery: trio.Nursery

    def __init__(self, background: BackgroundManager):
        self.background = background
        self.send_channel, self.receive_channel = trio.open_memory_channel(0)
        self.initial_convert = self.background.convert
        self.initial_nursery = self.background.nursery
        self.nursery_manager = trio.open_nursery()

    def convert(self, coroutine: typing.Callable) -> typing.Callable:
        async def wrapped(*args: typing.Any) -> None:
            await self.send_channel.send(await coroutine(*args))

        return wrapped

    async def __aenter__(self) -> None:
        self.background.convert = self.convert
        self.nursery = await self.nursery_manager.__aenter__()
        self.background.nursery = self.nursery

    async def __aexit__(self, *args: typing.Any) -> None:
        await self.receive_channel.receive()
        self.nursery.cancel_scope.cancel()
        await self.nursery.__aexit__(*args)
        self.background.convert = self.initial_convert
        self.background.nursery = self.initial_nursery
