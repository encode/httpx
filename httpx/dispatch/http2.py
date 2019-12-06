import functools
import typing

import h2.connection
import h2.events
from h2.settings import SettingCodes, Settings

from ..concurrency.base import (
    BaseEvent,
    BaseSocketStream,
    ConcurrencyBackend,
    TimeoutFlag,
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
        self.h2_state = h2.connection.H2Connection()
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]
        self.timeout_flags = {}  # type: typing.Dict[int, TimeoutFlag]
        self.window_update_received = {}  # type: typing.Dict[int, BaseEvent]

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
            self.init_complete.set()
        else:
            # All other streams need to wait until the connection is established.
            await self.init_complete.wait()

        stream_id = await self.send_headers(request, timeout)

        self.events[stream_id] = []
        self.timeout_flags[stream_id] = TimeoutFlag()
        self.window_update_received[stream_id] = self.backend.create_event()

        status_code: typing.Optional[int] = None
        headers: typing.Optional[list] = None

        async def receive_response(stream_id: int, timeout: Timeout) -> None:
            nonlocal status_code, headers
            status_code, headers = await self.receive_response(stream_id, timeout)

        await self.backend.fork(
            self.send_request_data,
            [stream_id, request.stream(), timeout],
            receive_response,
            [stream_id, timeout],
        )

        assert status_code is not None
        assert headers is not None

        content = self.body_iter(stream_id, timeout)
        on_close = functools.partial(self.response_closed, stream_id=stream_id)

        return Response(
            status_code=status_code,
            http_version="HTTP/2",
            headers=headers,
            content=content,
            on_close=on_close,
            request=request,
        )

    async def close(self) -> None:
        await self.socket.close()

    async def send_connection_init(self, timeout: Timeout) -> None:
        # Need to set these manually here instead of manipulating via
        # __setitem__() otherwise the H2Connection will emit SettingsUpdate
        # frames in addition to sending the undesired defaults.
        self.h2_state.local_settings = Settings(
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
        del self.h2_state.local_settings[
            h2.settings.SettingCodes.ENABLE_CONNECT_PROTOCOL
        ]

        self.h2_state.initiate_connection()
        data_to_send = self.h2_state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def send_headers(self, request: Request, timeout: Timeout) -> int:
        stream_id = self.h2_state.get_next_available_stream_id()
        headers = [
            (b":method", request.method.encode("ascii")),
            (b":authority", request.url.authority.encode("ascii")),
            (b":scheme", request.url.scheme.encode("ascii")),
            (b":path", request.url.full_path.encode("ascii")),
        ] + [(k, v) for k, v in request.headers.raw if k != b"host"]

        logger.trace(
            f"send_headers "
            f"stream_id={stream_id} "
            f"method={request.method!r} "
            f"target={request.url.full_path!r} "
            f"headers={headers!r}"
        )
        self.h2_state.send_headers(stream_id, headers)
        data_to_send = self.h2_state.data_to_send()
        await self.socket.write(data_to_send, timeout)
        return stream_id

    async def send_request_data(
        self, stream_id: int, stream: typing.AsyncIterator[bytes], timeout: Timeout,
    ) -> None:
        try:
            async for data in stream:
                await self.send_data(stream_id, data, timeout)
            await self.end_stream(stream_id, timeout)
        finally:
            # Once we've sent the request we should enable read timeouts.
            self.timeout_flags[stream_id].set_read_timeouts()

    async def send_data(self, stream_id: int, data: bytes, timeout: Timeout) -> None:
        while data:
            # The data will be divided into frames to send based on the flow control
            # window and the maximum frame size. Because the flow control window
            # can decrease in size, even possibly to zero, this will loop until all the
            # data is sent. In http2 specification:
            # https://tools.ietf.org/html/rfc7540#section-6.9
            flow_control = self.h2_state.local_flow_control_window(stream_id)
            chunk_size = min(
                len(data), flow_control, self.h2_state.max_outbound_frame_size
            )
            if chunk_size == 0:
                # this means that the flow control window is 0 (either for the stream
                # or the connection one), and no data can be sent until the flow control
                # window is updated.
                await self.window_update_received[stream_id].wait()
                self.window_update_received[stream_id].clear()
            else:
                chunk, data = data[:chunk_size], data[chunk_size:]
                self.h2_state.send_data(stream_id, chunk)
                data_to_send = self.h2_state.data_to_send()
                await self.socket.write(data_to_send, timeout)

    async def end_stream(self, stream_id: int, timeout: Timeout) -> None:
        logger.trace(f"end_stream stream_id={stream_id}")
        self.h2_state.end_stream(stream_id)
        data_to_send = self.h2_state.data_to_send()
        await self.socket.write(data_to_send, timeout)

    async def receive_response(
        self, stream_id: int, timeout: Timeout
    ) -> typing.Tuple[int, typing.List[typing.Tuple[bytes, bytes]]]:
        """
        Read the response status and headers from the network.
        """
        while True:
            event = await self.receive_event(stream_id, timeout)
            # As soon as we start seeing response events, we should enable
            # read timeouts, if we haven't already.
            self.timeout_flags[stream_id].set_read_timeouts()
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

    async def body_iter(
        self, stream_id: int, timeout: Timeout
    ) -> typing.AsyncIterator[bytes]:
        while True:
            event = await self.receive_event(stream_id, timeout)
            if isinstance(event, h2.events.DataReceived):
                self.h2_state.acknowledge_received_data(
                    event.flow_controlled_length, stream_id
                )
                yield event.data
            elif isinstance(event, (h2.events.StreamEnded, h2.events.StreamReset)):
                break

    async def receive_event(self, stream_id: int, timeout: Timeout) -> h2.events.Event:
        while not self.events[stream_id]:
            flag = self.timeout_flags[stream_id]
            data = await self.socket.read(self.READ_NUM_BYTES, timeout, flag=flag)
            events = self.h2_state.receive_data(data)
            for event in events:
                event_stream_id = getattr(event, "stream_id", 0)
                logger.trace(
                    f"receive_event stream_id={event_stream_id} event={event!r}"
                )

                if hasattr(event, "error_code"):
                    raise ProtocolError(event)

                if isinstance(event, h2.events.WindowUpdated):
                    if event_stream_id == 0:
                        for window_update_event in self.window_update_received.values():
                            window_update_event.set()
                    else:
                        try:
                            self.window_update_received[event_stream_id].set()
                        except KeyError:  # pragma: no cover
                            # the window_update_received dictionary is only relevant
                            # when sending data, which should never raise a KeyError
                            # here.
                            pass

                if event_stream_id:
                    self.events[event.stream_id].append(event)

            data_to_send = self.h2_state.data_to_send()
            await self.socket.write(data_to_send, timeout)

        return self.events[stream_id].pop(0)

    async def response_closed(self, stream_id: int) -> None:
        del self.events[stream_id]
        del self.timeout_flags[stream_id]
        del self.window_update_received[stream_id]

        if not self.events and self.on_release is not None:
            await self.on_release()

    @property
    def is_closed(self) -> bool:
        return False

    def is_connection_dropped(self) -> bool:
        return self.socket.is_connection_dropped()
