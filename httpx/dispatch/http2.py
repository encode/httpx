import typing

import h2.connection
import h2.events
from h2.settings import SettingCodes, Settings

from ..concurrency.base import (
    BaseEvent,
    BaseSocketStream,
    ConcurrencyBackend,
    lookup_backend,
)
from ..config import Timeout
from ..exceptions import ProtocolError
from ..models import Request, Response
from ..utils import get_logger

logger = get_logger(__name__)


class HTTP2Connection:
    READ_NUM_BYTES = 4096

    def __init__(
        self,
        socket: BaseSocketStream,
        backend: typing.Union[str, ConcurrencyBackend] = "auto",
        on_release: typing.Callable = None,
    ):
        self.socket = socket
        self.backend = lookup_backend(backend)
        self.on_release = on_release
        self.state = h2.connection.H2Connection()

        self.streams = {}  # type: typing.Dict[int, HTTP2Stream]
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]

        self.init_started = False

    @property
    def init_complete(self) -> BaseEvent:
        # We do this lazily, to make sure backend autodetection always
        # runs within an async context.
        if not hasattr(self, "_initialization_complete"):
            self._initialization_complete = self.backend.create_event()
        return self._initialization_complete

    async def send(self, request: Request, timeout: Timeout = None) -> Response:
        timeout = Timeout() if timeout is None else timeout

        if not self.init_started:
            # The very first stream is responsible for initiating the connection.
            self.init_started = True
            await self.send_connection_init(timeout)
            stream_id = self.state.get_next_available_stream_id()
            self.init_complete.set()
        else:
            # All other streams need to wait until the connection is established.
            await self.init_complete.wait()
            stream_id = self.state.get_next_available_stream_id()

        stream = HTTP2Stream(stream_id=stream_id, connection=self, state=self.state)
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
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    @property
    def is_closed(self) -> bool:
        return False

    def is_connection_dropped(self) -> bool:
        return self.socket.is_connection_dropped()

    async def close(self) -> None:
        await self.socket.close()

    async def receive_event(self, stream_id: int, timeout: Timeout) -> h2.events.Event:
        """
        Streams call into `connection.receive_event()` in order to read events
        from the network. The connection manages holding onto any events that
        have not yet been pulled by a stream.
        """
        while not self.events[stream_id]:
            data = await self.socket.read(self.READ_NUM_BYTES, timeout)
            events = self.state.receive_data(data)
            for event in events:
                event_stream_id = getattr(event, "stream_id", 0)
                logger.trace(
                    f"receive_event stream_id={event_stream_id} event={event!r}"
                )

                if hasattr(event, "error_code"):
                    raise ProtocolError(event)

                if isinstance(event, h2.events.WindowUpdated) and event_stream_id == 0:
                    for events in self.events.values():
                        events.append(event)

                if event_stream_id in self.events:
                    self.events[event_stream_id].append(event)

            data_to_send = self.state.data_to_send()
            await self.socket.write(data_to_send, timeout)

        return self.events[stream_id].pop(0)

    async def send_data(self, timeout: Timeout) -> None:
        data_to_send = self.state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def close_stream(self, stream_id: int) -> None:
        del self.streams[stream_id]
        del self.events[stream_id]

        if not self.streams and self.on_release is not None:
            await self.on_release()


class HTTP2Stream:
    def __init__(
        self,
        stream_id: int,
        connection: HTTP2Connection,
        state: h2.connection.H2Connection,
    ) -> None:
        self.stream_id = stream_id
        self.connection = connection
        self.state = state

    async def send(self, request: Request, timeout: Timeout) -> Response:
        # Send the request.
        await self.send_headers(request, timeout)
        async for data in request.stream():
            await self.send_data(data, timeout)
        await self.end_stream(timeout)

        # Receive the response.
        status_code, headers = await self.receive_response(timeout)
        content = self.body_iter(timeout)
        return Response(
            status_code=status_code,
            http_version="HTTP/2",
            headers=headers,
            content=content,
            on_close=self.close,
            request=request,
        )

    async def send_headers(self, request: Request, timeout: Timeout) -> None:
        headers = [
            (b":method", request.method.encode("ascii")),
            (b":authority", request.url.authority.encode("ascii")),
            (b":scheme", request.url.scheme.encode("ascii")),
            (b":path", request.url.full_path.encode("ascii")),
        ] + [(k, v) for k, v in request.headers.raw if k != b"host"]

        logger.trace(
            f"send_headers "
            f"stream_id={self.stream_id} "
            f"method={request.method!r} "
            f"target={request.url.full_path!r} "
            f"headers={headers!r}"
        )
        self.state.send_headers(self.stream_id, headers)
        await self.connection.send_data(timeout)

    async def send_data(self, data: bytes, timeout: Timeout) -> None:
        while data:
            # The data will be divided into frames to send based on the flow control
            # window and the maximum frame size. Because the flow control window
            # can decrease in size, even possibly to zero, this will loop until all the
            # data is sent. In http2 specification:
            # https://tools.ietf.org/html/rfc7540#section-6.9
            flow_control = self.state.local_flow_control_window(self.stream_id)
            chunk_size = min(
                len(data), flow_control, self.state.max_outbound_frame_size
            )
            if chunk_size == 0:
                # The flow control window is 0 (either for the stream or the
                # connection one), and no data can be sent until the flow
                # control window is updated.
                while True:
                    event = await self.connection.receive_event(self.stream_id, timeout)
                    if isinstance(event, h2.events.WindowUpdated):
                        break
            else:
                chunk, data = data[:chunk_size], data[chunk_size:]
                self.state.send_data(self.stream_id, chunk)
                await self.connection.send_data(timeout)

    async def end_stream(self, timeout: Timeout) -> None:
        logger.trace(f"end_stream stream_id={self.stream_id}")
        self.state.end_stream(self.stream_id)
        await self.connection.send_data(timeout)

    async def receive_response(
        self, timeout: Timeout
    ) -> typing.Tuple[int, typing.List[typing.Tuple[bytes, bytes]]]:
        """
        Read the response status and headers from the network.
        """
        while True:
            event = await self.connection.receive_event(self.stream_id, timeout)

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
            event = await self.connection.receive_event(self.stream_id, timeout)
            if isinstance(event, h2.events.DataReceived):
                self.state.acknowledge_received_data(
                    event.flow_controlled_length, self.stream_id
                )
                yield event.data
            elif isinstance(event, (h2.events.StreamEnded, h2.events.StreamReset)):
                break

    async def close(self) -> None:
        await self.connection.close_stream(self.stream_id)
