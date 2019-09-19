import typing

import h11

from ..concurrency.base import BaseTCPStream, ConcurrencyBackend, TimeoutFlag
from ..config import TimeoutConfig, TimeoutTypes
from ..models import AsyncRequest, AsyncResponse
from ..utils import get_logger

H11Event = typing.Union[
    h11.Request,
    h11.Response,
    h11.InformationalResponse,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


# Callback signature: async def callback() -> None
# In practice the callback will be a functools partial, which binds
# the `ConnectionPool.release_connection(conn: HTTPConnection)` method.
OnReleaseCallback = typing.Callable[[], typing.Awaitable[None]]


logger = get_logger(__name__)


class HTTP11Connection:
    READ_NUM_BYTES = 4096

    def __init__(
        self,
        stream: BaseTCPStream,
        backend: ConcurrencyBackend,
        on_release: typing.Optional[OnReleaseCallback] = None,
    ):
        self.stream = stream
        self.backend = backend
        self.on_release = on_release
        self.h11_state = h11.Connection(our_role=h11.CLIENT)
        self.timeout_flag = TimeoutFlag()

    async def send(
        self, request: AsyncRequest, timeout: TimeoutTypes = None
    ) -> AsyncResponse:
        timeout = None if timeout is None else TimeoutConfig(timeout)

        await self._send_request(request, timeout)

        task, args = self._send_request_data, [request.stream(), timeout]
        async with self.backend.background_manager(task, *args):
            http_version, status_code, headers = await self._receive_response(timeout)
        content = self._receive_response_data(timeout)

        return AsyncResponse(
            status_code=status_code,
            http_version=http_version,
            headers=headers,
            content=content,
            on_close=self.response_closed,
            request=request,
        )

    async def close(self) -> None:
        event = h11.ConnectionClosed()
        try:
            logger.debug(f"send_event event={event!r}")
            self.h11_state.send(event)
        except h11.LocalProtocolError:  # pragma: no cover
            # Premature client disconnect
            pass
        await self.stream.close()

    async def _send_request(
        self, request: AsyncRequest, timeout: TimeoutConfig = None
    ) -> None:
        """
        Send the request method, URL, and headers to the network.
        """
        logger.debug(
            f"send_headers method={request.method!r} "
            f"target={request.url.full_path!r} "
            f"headers={request.headers!r}"
        )

        method = request.method.encode("ascii")
        target = request.url.full_path.encode("ascii")
        headers = request.headers.raw
        event = h11.Request(method=method, target=target, headers=headers)
        await self._send_event(event, timeout)

    async def _send_request_data(
        self, data: typing.AsyncIterator[bytes], timeout: TimeoutConfig = None
    ) -> None:
        """
        Send the request body to the network.
        """
        try:
            # Send the request body.
            async for chunk in data:
                logger.debug(f"send_data data=Data(<{len(chunk)} bytes>)")
                event = h11.Data(data=chunk)
                await self._send_event(event, timeout)

            # Finalize sending the request.
            event = h11.EndOfMessage()
            await self._send_event(event, timeout)
        except OSError:  # pragma: nocover
            # Once we've sent the initial part of the request we don't actually
            # care about connection errors that occur when sending the body.
            # Ignore these, and defer to any exceptions on reading the response.
            self.h11_state.send_failed()
        finally:
            # Once we've sent the request, we enable read timeouts.
            self.timeout_flag.set_read_timeouts()

    async def _send_event(self, event: H11Event, timeout: TimeoutConfig = None) -> None:
        """
        Send a single `h11` event to the network, waiting for the data to
        drain before returning.
        """
        bytes_to_send = self.h11_state.send(event)
        await self.stream.write(bytes_to_send, timeout)

    async def _receive_response(
        self, timeout: TimeoutConfig = None
    ) -> typing.Tuple[str, int, typing.List[typing.Tuple[bytes, bytes]]]:
        """
        Read the response status and headers from the network.
        """
        while True:
            event = await self._receive_event(timeout)
            # As soon as we start seeing response events, we should enable
            # read timeouts, if we haven't already.
            self.timeout_flag.set_read_timeouts()
            if isinstance(event, h11.InformationalResponse):
                continue
            else:
                assert isinstance(event, h11.Response)
                break  # pragma: no cover
        http_version = "HTTP/%s" % event.http_version.decode("latin-1", errors="ignore")
        return http_version, event.status_code, event.headers

    async def _receive_response_data(
        self, timeout: TimeoutConfig = None
    ) -> typing.AsyncIterator[bytes]:
        """
        Read the response data from the network.
        """
        while True:
            event = await self._receive_event(timeout)
            if isinstance(event, h11.Data):
                yield bytes(event.data)
            else:
                assert isinstance(event, h11.EndOfMessage) or event is h11.PAUSED
                break  # pragma: no cover

    async def _receive_event(self, timeout: TimeoutConfig = None) -> H11Event:
        """
        Read a single `h11` event, reading more data from the network if needed.
        """
        while True:
            event = self.h11_state.next_event()

            if isinstance(event, h11.Data):
                logger.debug(f"receive_event event=Data(<{len(event.data)} bytes>)")
            else:
                logger.debug(f"receive_event event={event!r}")

            if event is h11.NEED_DATA:
                try:
                    data = await self.stream.read(
                        self.READ_NUM_BYTES, timeout, flag=self.timeout_flag
                    )
                except OSError:  # pragma: nocover
                    data = b""
                self.h11_state.receive_data(data)
            else:
                assert event is not h11.NEED_DATA
                break  # pragma: no cover
        return event

    async def response_closed(self) -> None:
        logger.debug(
            f"response_closed "
            f"our_state={self.h11_state.our_state!r} "
            f"their_state={self.h11_state.their_state}"
        )
        if (
            self.h11_state.our_state is h11.DONE
            and self.h11_state.their_state is h11.DONE
        ):
            # Get ready for another request/response cycle.
            self.h11_state.start_next_cycle()
            self.timeout_flag.set_write_timeouts()
        else:
            await self.close()

        if self.on_release is not None:
            await self.on_release()

    @property
    def is_closed(self) -> bool:
        return self.h11_state.our_state in (h11.CLOSED, h11.ERROR)

    def is_connection_dropped(self) -> bool:
        return self.stream.is_connection_dropped()
