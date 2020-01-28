import typing

import h2.connection
import h2.events
from h2.config import H2Configuration
from h2.settings import SettingCodes, Settings

from .._backends.base import (
    BaseLock,
    BaseSocketStream,
    ConcurrencyBackend,
    lookup_backend,
)
from .._config import Timeout
from .._content_streams import AsyncIteratorStream
from .._exceptions import ProtocolError
from .._models import Request, Response
from .._utils import get_logger

logger = get_logger(__name__)


class HTTP2Connection:
    READ_NUM_BYTES = 4096
    CONFIG = H2Configuration(validate_inbound_headers=False)

    def __init__(
        self,
        socket: BaseSocketStream,
        backend: typing.Union[str, ConcurrencyBackend] = "auto",
        on_release: typing.Callable = None,
    ):
        self.socket = socket
        self.backend = lookup_backend(backend)
        self.on_release = on_release
        self.state = h2.connection.H2Connection(config=self.CONFIG)

        self.streams = {}  # type: typing.Dict[int, HTTP2Stream]
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]

        self.sent_connection_init = False

    @property
    def is_http2(self) -> bool:
        return True

    @property
    def init_lock(self) -> BaseLock:
        # We do this lazily, to make sure backend autodetection always
        # runs within an async context.
        if not hasattr(self, "_initialization_lock"):
            self._initialization_lock = self.backend.create_lock()
        return self._initialization_lock

    async def send(self, request: Request, timeout: Timeout = None) -> Response:
        timeout = Timeout() if timeout is None else timeout

        async with self.init_lock:
            if not self.sent_connection_init:
                # The very first stream is responsible for initiating the connection.
                await self.send_connection_init(timeout)
                self.sent_connection_init = True
            stream_id = self.state.get_next_available_stream_id()

        stream = HTTP2Stream(stream_id=stream_id, connection=self)
        self.streams[stream_id] = stream
        self.events[stream_id] = []
        return await stream.send(request, timeout)

    async def send_connection_init(self, timeout: Timeout) -> None:
        """
        The HTTP/2 connection requires some initial setup before we can start
        using individual request/response streams on it.
        """

        # Need to set these manually here instead of manipulating via
        # __setitem__() otherwise the H2Connection will emit SettingsUpdate
        # frames in addition to sending the undesired defaults.
        self.state.local_settings = Settings(
            client=True,
            initial_values={
                # Disable PUSH_PROMISE frames from the server since we don't do anything
                # with them for now.  Maybe when we support caching?
                SettingCodes.ENABLE_PUSH: 0,
                # These two are taken from h2 for safe defaults
                SettingCodes.MAX_CONCURRENT_STREAMS: 100,
                SettingCodes.MAX_HEADER_LIST_SIZE: 65536,
            },
        )

        # Some websites (*cough* Yahoo *cough*) balk at this setting being
        # present in the initial handshake since it's not defined in the original
        # RFC despite the RFC mandating ignoring settings you don't know about.
        del self.state.local_settings[h2.settings.SettingCodes.ENABLE_CONNECT_PROTOCOL]

        self.state.initiate_connection()
        self.state.increment_flow_control_window(2 ** 24)
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    @property
    def is_closed(self) -> bool:
        return False

    def is_connection_dropped(self) -> bool:
        return self.socket.is_connection_dropped()

    async def close(self) -> None:
        await self.socket.close()

    async def wait_for_outgoing_flow(self, stream_id: int, timeout: Timeout) -> int:
        """
        Returns the maximum allowable outgoing flow for a given stream.

        If the allowable flow is zero, then waits on the network until
        WindowUpdated frames have increased the flow rate.

        https://tools.ietf.org/html/rfc7540#section-6.9
        """
        local_flow = self.state.local_flow_control_window(stream_id)
        connection_flow = self.state.max_outbound_frame_size
        flow = min(local_flow, connection_flow)
        while flow == 0:
            await self.receive_events(timeout)
            local_flow = self.state.local_flow_control_window(stream_id)
            connection_flow = self.state.max_outbound_frame_size
            flow = min(local_flow, connection_flow)
        return flow

    async def wait_for_event(self, stream_id: int, timeout: Timeout) -> h2.events.Event:
        """
        Returns the next event for a given stream.

        If no events are available yet, then waits on the network until
        an event is available.
        """
        while not self.events[stream_id]:
            await self.receive_events(timeout)
        return self.events[stream_id].pop(0)

    async def receive_events(self, timeout: Timeout) -> None:
        """
        Read some data from the network, and update the H2 state.
        """
        data = await self.socket.read(self.READ_NUM_BYTES, timeout)
        events = self.state.receive_data(data)
        for event in events:
            event_stream_id = getattr(event, "stream_id", 0)
            logger.trace(f"receive_event stream_id={event_stream_id} event={event!r}")

            if hasattr(event, "error_code"):
                raise ProtocolError(event)

            if event_stream_id in self.events:
                self.events[event_stream_id].append(event)

        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def send_headers(
        self,
        stream_id: int,
        headers: typing.List[typing.Tuple[bytes, bytes]],
        end_stream: bool,
        timeout: Timeout,
    ) -> None:
        self.state.send_headers(stream_id, headers, end_stream=end_stream)
        self.state.increment_flow_control_window(2 ** 24, stream_id=stream_id)
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def send_data(self, stream_id: int, chunk: bytes, timeout: Timeout) -> None:
        self.state.send_data(stream_id, chunk)
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def end_stream(self, stream_id: int, timeout: Timeout) -> None:
        self.state.end_stream(stream_id)
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def acknowledge_received_data(
        self, stream_id: int, amount: int, timeout: Timeout
    ) -> None:
        self.state.acknowledge_received_data(amount, stream_id)
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def close_stream(self, stream_id: int) -> None:
        del self.streams[stream_id]
        del self.events[stream_id]

        if not self.streams and self.on_release is not None:
            await self.on_release()


class HTTP2Stream:
    def __init__(self, stream_id: int, connection: HTTP2Connection) -> None:
        self.stream_id = stream_id
        self.connection = connection

    async def send(self, request: Request, timeout: Timeout) -> Response:
        # Send the request.
        has_body = (
            "Content-Length" in request.headers
            or "Transfer-Encoding" in request.headers
        )

        await self.send_headers(request, has_body, timeout)
        if has_body:
            await self.send_body(request, timeout)

        # Receive the response.
        status_code, headers = await self.receive_response(timeout)
        stream = AsyncIteratorStream(
            aiterator=self.body_iter(timeout), close_func=self.close
        )

        return Response(
            status_code=status_code,
            http_version="HTTP/2",
            headers=headers,
            stream=stream,
            request=request,
        )

    async def send_headers(
        self, request: Request, has_body: bool, timeout: Timeout
    ) -> None:
        headers = [
            (b":method", request.method.encode("ascii")),
            (b":authority", request.url.authority.encode("ascii")),
            (b":scheme", request.url.scheme.encode("ascii")),
            (b":path", request.url.full_path.encode("ascii")),
        ] + [
            (k, v)
            for k, v in request.headers.raw
            if k not in (b"host", b"transfer-encoding")
        ]
        end_stream = not has_body

        logger.trace(
            f"send_headers "
            f"stream_id={self.stream_id} "
            f"method={request.method!r} "
            f"target={request.url.full_path!r} "
            f"headers={headers!r}"
        )
        await self.connection.send_headers(self.stream_id, headers, end_stream, timeout)

    async def send_body(self, request: Request, timeout: Timeout) -> None:
        logger.trace(f"send_body stream_id={self.stream_id}")
        async for data in request.stream:
            while data:
                max_flow = await self.connection.wait_for_outgoing_flow(
                    self.stream_id, timeout
                )
                chunk_size = min(len(data), max_flow)
                chunk, data = data[:chunk_size], data[chunk_size:]
                await self.connection.send_data(self.stream_id, chunk, timeout)

        await self.connection.end_stream(self.stream_id, timeout)

    async def receive_response(
        self, timeout: Timeout
    ) -> typing.Tuple[int, typing.List[typing.Tuple[bytes, bytes]]]:
        """
        Read the response status and headers from the network.
        """
        while True:
            event = await self.connection.wait_for_event(self.stream_id, timeout)
            if isinstance(event, h2.events.ResponseReceived):
                break

        status_code = 200
        headers = []
        for k, v in event.headers:
            if k == b":status":
                status_code = int(v.decode("ascii", errors="ignore"))
            elif not k.startswith(b":"):
                headers.append((k, v))

        return (status_code, headers)

    async def body_iter(self, timeout: Timeout) -> typing.AsyncIterator[bytes]:
        while True:
            event = await self.connection.wait_for_event(self.stream_id, timeout)
            if isinstance(event, h2.events.DataReceived):
                amount = event.flow_controlled_length
                await self.connection.acknowledge_received_data(
                    self.stream_id, amount, timeout
                )
                yield event.data
            elif isinstance(event, (h2.events.StreamEnded, h2.events.StreamReset)):
                break

    async def close(self) -> None:
        await self.connection.close_stream(self.stream_id)
