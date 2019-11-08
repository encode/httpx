import asyncio
import concurrent.futures
import functools
import ssl
import sys
import threading
import time
import typing
from types import TracebackType

from ..config import PoolLimits, TimeoutConfig
from ..exceptions import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from ..utils import get_logger
from .base import (
    BaseBackgroundManager,
    BaseEvent,
    BasePoolSemaphore,
    BaseQueue,
    BaseTCPStream,
    ConcurrencyBackend,
    TimeoutFlag,
)

SSL_MONKEY_PATCH_APPLIED = False

logger = get_logger(__name__)


def ssl_monkey_patch() -> None:
    """
    Monkey-patch for https://bugs.python.org/issue36709

    This prevents console errors when outstanding HTTPS connections
    still exist at the point of exiting.

    Clients which have been opened using a `with` block, or which have
    had `close()` closed, will not exhibit this issue in the first place.
    """
    MonkeyPatch = asyncio.selector_events._SelectorSocketTransport  # type: ignore

    _write = MonkeyPatch.write

    def _fixed_write(self, data: bytes) -> None:  # type: ignore
        if self._loop and not self._loop.is_closed():
            _write(self, data)

    MonkeyPatch.write = _fixed_write


class TCPStream(BaseTCPStream):
    def __init__(
        self,
        stream_reader: asyncio.StreamReader,
        stream_writer: asyncio.StreamWriter,
        timeout: TimeoutConfig,
    ):
        self.stream_reader = stream_reader
        self.stream_writer = stream_writer
        self.timeout = timeout

        self._inner: typing.Optional[TCPStream] = None

    async def start_tls(
        self, hostname: str, ssl_context: ssl.SSLContext, timeout: TimeoutConfig
    ) -> BaseTCPStream:
        loop = asyncio.get_event_loop()
        if not hasattr(loop, "start_tls"):  # pragma: no cover
            raise NotImplementedError(
                "asyncio.AbstractEventLoop.start_tls() is only available in Python 3.7+"
            )

        stream_reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(stream_reader)
        transport = self.stream_writer.transport

        loop_start_tls = loop.start_tls  # type: ignore
        transport = await asyncio.wait_for(
            loop_start_tls(
                transport=transport,
                protocol=protocol,
                sslcontext=ssl_context,
                server_hostname=hostname,
            ),
            timeout=timeout.connect_timeout,
        )

        stream_reader.set_transport(transport)
        stream_writer = asyncio.StreamWriter(
            transport=transport, protocol=protocol, reader=stream_reader, loop=loop
        )

        ssl_stream = TCPStream(stream_reader, stream_writer, self.timeout)
        # When we return a new TCPStream with new StreamReader/StreamWriter instances,
        # we need to keep references to the old StreamReader/StreamWriter so that they
        # are not garbage collected and closed while we're still using them.
        ssl_stream._inner = self
        return ssl_stream

    def get_http_version(self) -> str:
        ssl_object = self.stream_writer.get_extra_info("ssl_object")

        if ssl_object is None:
            return "HTTP/1.1"

        ident = ssl_object.selected_alpn_protocol()
        return "HTTP/2" if ident == "h2" else "HTTP/1.1"

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
            try:
                data = await asyncio.wait_for(self.stream_reader.read(n), read_timeout)
                break
            except asyncio.TimeoutError:
                if should_raise:
                    raise ReadTimeout() from None
                # FIX(py3.6): yield control back to the event loop to give it a chance
                # to cancel `.read(n)` before we retry.
                # This prevents concurrent `.read()` calls, which asyncio
                # doesn't seem to allow on 3.6.
                # See: https://github.com/encode/httpx/issues/382
                await asyncio.sleep(0)

        return data

    def write_no_block(self, data: bytes) -> None:
        self.stream_writer.write(data)  # pragma: nocover

    async def write(
        self, data: bytes, timeout: TimeoutConfig = None, flag: TimeoutFlag = None
    ) -> None:
        if not data:
            return

        if timeout is None:
            timeout = self.timeout

        self.stream_writer.write(data)
        while True:
            try:
                await asyncio.wait_for(  # type: ignore
                    self.stream_writer.drain(), timeout.write_timeout
                )
                break
            except asyncio.TimeoutError:
                # We check our flag at the first possible moment, in order to
                # allow us to suppress write timeouts, if we've since
                # switched over to read-timeout mode.
                should_raise = flag is None or flag.raise_on_write_timeout
                if should_raise:
                    raise WriteTimeout() from None

    def is_connection_dropped(self) -> bool:
        # Counter-intuitively, what we really want to know here is whether the socket is
        # *readable*, i.e. whether it would return immediately with empty bytes if we
        # called `.recv()` on it, indicating that the other end has closed the socket.
        # See: https://github.com/encode/httpx/pull/143#issuecomment-515181778
        #
        # As it turns out, asyncio checks for readability in the background
        # (see: https://github.com/encode/httpx/pull/276#discussion_r322000402),
        # so checking for EOF or readability here would yield the same result.
        #
        # At the cost of rigour, we check for EOF instead of readability because asyncio
        # does not expose any public API to check for readability.
        # (For a solution that uses private asyncio APIs, see:
        # https://github.com/encode/httpx/pull/143#issuecomment-515202982)

        return self.stream_reader.at_eof()

    async def close(self) -> None:
        self.stream_writer.close()
        if sys.version_info >= (3, 7):
            await self.stream_writer.wait_closed()


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
    worker_thread_id: typing.Optional[int] = None

    def __init__(self) -> None:
        global SSL_MONKEY_PATCH_APPLIED

        if not SSL_MONKEY_PATCH_APPLIED:
            ssl_monkey_patch()
        SSL_MONKEY_PATCH_APPLIED = True

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not hasattr(self, "_loop"):
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
            self._loop_thread_id = threading.get_ident()

        return self._loop

    @property
    def worker_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """
        A thread executor where coroutines should be run if
        the event loop of the main thread is already running.

        It is important to have only one worker thread, because sync HTTP calls
        will create tasks that manipulate I/O resources (namely iterate request body,
        get response, close response), and those tasks MUST be running in the
        same thread.
        """
        # NOTE: currently, the worker executor is never shutdown. It may block
        # the interpreter from exiting if the worker thread is pending or blocked.
        if not hasattr(self, "_worker_executor"):
            self._worker_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        return self._worker_executor

    @property
    def worker_loop(self) -> asyncio.AbstractEventLoop:
        """The event loop attached to the worker thread.

        It is important to keep a reference to the worker event loop, because sync
        HTTP calls will create tasks that manipulate I/O resources (namely iterate
        request body, get response, close response), and those tasks MUST be bound to
        the same event loop.
        """
        if threading.get_ident() == threading.main_thread().ident:
            raise RuntimeError("Cannot only access worker loop from a sub-thread")

        if not hasattr(self, "_worker_loop"):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            self._worker_loop = loop

        return self._worker_loop

    async def open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseTCPStream:
        try:
            stream_reader, stream_writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(hostname, port, ssl=ssl_context),
                timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

        return TCPStream(
            stream_reader=stream_reader, stream_writer=stream_writer, timeout=timeout
        )

    async def run_in_threadpool(
        self, func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        if kwargs:
            # loop.run_in_executor doesn't accept 'kwargs', so bind them in here
            func = functools.partial(func, **kwargs)
        return await self.loop.run_in_executor(None, func, *args)

    def run(
        self, coroutine: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any:
        initial_loop = self.loop

        target: typing.Callable

        if (
            initial_loop.is_running()
            and threading.main_thread().ident == threading.get_ident()
        ):
            # The event loop is already running in this thread.
            # We must run 'coroutine' on the worker loop in the worker thread.

            def target(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
                def _target() -> typing.Any:
                    if self.worker_thread_id is None:
                        self.worker_thread_id = threading.get_ident()

                    assert self.worker_thread_id is not None
                    assert threading.get_ident() == self.worker_thread_id

                    self._loop = self.worker_loop
                    return self.loop.run_until_complete(coroutine(*args, **kwargs))

                future = self.worker_executor.submit(_target)
                while not future.done():
                    time.sleep(1e-2)
                return future.result()

        elif initial_loop.is_running():
            if self.worker_thread_id is None:
                self.worker_thread_id = threading.get_ident()

            assert self.worker_thread_id is not None
            assert threading.get_ident() == self.worker_thread_id
            # The loop is running in a different thread (i.e. the main thread)
            # Run 'coroutine' on the existing loop, but from this thread (i.e.
            # the worker thread).

            def target(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
                # 1) Create a future to hold the result.
                call_result: concurrent.futures.Future[typing.Any] = (
                    concurrent.futures.Future()
                )
                # 2) Schedule the coroutine on the event loop of the main thread,
                # so that it sets its result or exception onto 'call_result'.
                self.loop.call_soon_threadsafe(
                    self.loop.create_task,
                    proxy_coroutine_to_future(
                        coroutine,
                        *args,
                        future=call_result,
                        exc_info=sys.exc_info(),
                        **kwargs,
                    ),
                )
                # Wait for the coroutine to terminate, i.e. for the future to have
                # a result set.
                while not call_result.done():
                    # This blocks the worker thread, which is fine because the
                    # event loop is still being driven in the main thread.
                    time.sleep(1e-2)
                return call_result.result()

        else:
            # Event loop is not running: we can run the coroutine on it directly.

            def target(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
                return initial_loop.run_until_complete(coroutine(*args, **kwargs))

        try:
            return target(*args, **kwargs)
        finally:
            self._loop = initial_loop

    def get_semaphore(self, limits: PoolLimits) -> BasePoolSemaphore:
        return PoolSemaphore(limits)

    def create_queue(self, max_size: int) -> BaseQueue:
        return typing.cast(BaseQueue, asyncio.Queue(maxsize=max_size))

    def create_event(self) -> BaseEvent:
        return typing.cast(BaseEvent, asyncio.Event())

    def background_manager(
        self, coroutine: typing.Callable, *args: typing.Any
    ) -> "BackgroundManager":
        return BackgroundManager(coroutine, args)


class BackgroundManager(BaseBackgroundManager):
    def __init__(self, coroutine: typing.Callable, args: typing.Any) -> None:
        self.coroutine = coroutine
        self.args = args

    async def __aenter__(self) -> "BackgroundManager":
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.coroutine(*self.args))
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.task
        if exc_type is None:
            self.task.result()


async def proxy_coroutine_to_future(
    coroutine: typing.Callable,
    *args: typing.Any,
    future: concurrent.futures.Future,
    exc_info: tuple,
    **kwargs: typing.Any,
) -> None:
    """Run a coroutine, and set its return value or exception on 'future'."""
    try:
        # If we have an exception, run the function inside the except
        # block after raising it so that 'exc_info' is correctly populated.
        if exc_info[1]:
            try:
                raise exc_info[1]
            except BaseException:
                result = await coroutine(*args, **kwargs)
        else:
            result = await coroutine(*args, **kwargs)
    except Exception as e:
        future.set_exception(e)
    else:
        future.set_result(result)
