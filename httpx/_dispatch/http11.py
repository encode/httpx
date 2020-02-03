import typing

import h11

from .._backends.base import BaseSocketStream
from .._config import Timeout
from .._content_streams import AsyncIteratorStream, ContentStream
from .._exceptions import ConnectionClosed, ProtocolError
from .._models import URL, Headers
from .._utils import get_logger

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
        socket: BaseSocketStream,
        on_release: typing.Optional[OnReleaseCallback] = None,
    ):
        self.socket = socket
        self.on_release = on_release
        self.h11_state = h11.Connection(our_role=h11.CLIENT)

    @property
    def is_http2(self) -> bool:
        return False

    async def send(
        self,
        method: bytes,
        url: URL,
        headers: Headers,
        stream: ContentStream,
        timeout: Timeout = None,
    ) -> typing.Tuple[int, str, Headers, ContentStream]:
        timeout = Timeout() if timeout is None else timeout

        await self._send_request(method, url, headers, timeout)
        await self._send_request_body(stream, timeout)
        http_version, status_code, raw_headers = await self._receive_response(timeout)
        stream = AsyncIteratorStream(
            aiterator=self._receive_response_data(timeout),
            close_func=self.response_closed,
        )

        return (status_code, http_version, Headers(raw_headers), stream)

    async def close(self) -> None:
        event = h11.ConnectionClosed()
        try:
            logger.trace(f"send_event event={event!r}")
            self.h11_state.send(event)
        except h11.LocalProtocolError:  # pragma: no cover
            # Premature client disconnect
            pass
        await self.socket.close()

    async def _send_request(
        self, method: bytes, url: URL, headers: Headers, timeout: Timeout,
    ) -> None:
        """
        Send the request method, URL, and headers to the network.
        """
        logger.trace(
            f"send_headers method={method!r} "
            f"target={url.full_path!r} "
            f"headers={headers!r}"
        )

        method = method
        if method == b"CONNECT":
            target = f"{url.host}:{url.port}".encode("ascii")
        else:
            target = url.full_path.encode("ascii")
        event = h11.Request(method=method, target=target, headers=headers.raw)
        await self._send_event(event, timeout)

    async def _send_request_body(self, stream: ContentStream, timeout: Timeout) -> None:
        """
        Send the request body to the network.
        """
        try:
            # Send the request body.
            async for chunk in stream:
                logger.trace(f"send_data data=Data(<{len(chunk)} bytes>)")
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

    async def _send_event(self, event: H11Event, timeout: Timeout) -> None:
        """
        Send a single `h11` event to the network, waiting for the data to
        drain before returning.
        """
        bytes_to_send = self.h11_state.send(event)
        await self.socket.write(bytes_to_send, timeout)

    async def _receive_response(
        self, timeout: Timeout
    ) -> typing.Tuple[str, int, typing.List[typing.Tuple[bytes, bytes]]]:
        """
        Read the response status and headers from the network.
        """
        while True:
            event = await self._receive_event(timeout)
            if isinstance(event, h11.InformationalResponse):
                continue
            else:
                assert isinstance(event, h11.Response)
                break  # pragma: no cover
        http_version = "HTTP/%s" % event.http_version.decode("latin-1", errors="ignore")
        return http_version, event.status_code, event.headers

    async def _receive_response_data(
        self, timeout: Timeout
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

    async def _receive_event(self, timeout: Timeout) -> H11Event:
        """
        Read a single `h11` event, reading more data from the network if needed.
        """
        while True:
            try:
                event = self.h11_state.next_event()
            except h11.RemoteProtocolError as e:
                logger.debug(
                    "h11.RemoteProtocolError exception "
                    + f"their_state={self.h11_state.their_state} "
                    + f"error_status_hint={e.error_status_hint}"
                )
                if self.socket.is_connection_dropped():
                    raise ConnectionClosed(e)
                raise ProtocolError(e)

            if isinstance(event, h11.Data):
                logger.trace(f"receive_event event=Data(<{len(event.data)} bytes>)")
            else:
                logger.trace(f"receive_event event={event!r}")

            if event is h11.NEED_DATA:
                try:
                    data = await self.socket.read(self.READ_NUM_BYTES, timeout)
                except OSError:  # pragma: nocover
                    data = b""
                self.h11_state.receive_data(data)
            else:
                assert event is not h11.NEED_DATA
                break  # pragma: no cover
        return event

    async def response_closed(self) -> None:
        logger.trace(
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
        else:
            await self.close()

        if self.on_release is not None:
            await self.on_release()

    @property
    def is_closed(self) -> bool:
        return self.h11_state.our_state in (h11.CLOSED, h11.ERROR)

    def is_connection_dropped(self) -> bool:
        return self.socket.is_connection_dropped()
