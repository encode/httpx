import functools
import typing

import h2.connection
import h2.events

from ..concurrency.base import BaseEvent, BaseTCPStream, ConcurrencyBackend, TimeoutFlag
from ..config import TimeoutConfig, TimeoutTypes
from ..models import AsyncRequest, AsyncResponse
from ..utils import get_logger

logger = get_logger(__name__)


class HTTP2Connection:
    READ_NUM_BYTES = 4096

    def __init__(
        self,
        stream: BaseTCPStream,
        backend: ConcurrencyBackend,
        on_release: typing.Callable = None,
    ):
        self.stream = stream
        self.backend = backend
        self.on_release = on_release
        self.h2_state = h2.connection.H2Connection()
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]
        self.timeout_flags = {}  # type: typing.Dict[int, TimeoutFlag]
        self.initialized = False
        self.window_update_received = {}  # type: typing.Dict[int, BaseEvent]

    async def send(
        self, request: AsyncRequest, timeout: TimeoutTypes = None
    ) -> AsyncResponse:
        timeout = None if timeout is None else TimeoutConfig(timeout)

        # Start sending the request.
        if not self.initialized:
            self.initiate_connection()

        stream_id = await self.send_headers(request, timeout)

        self.events[stream_id] = []
        self.timeout_flags[stream_id] = TimeoutFlag()
        self.window_update_received[stream_id] = self.backend.create_event()

        task, args = self.send_request_data, [stream_id, request.stream(), timeout]
        async with self.backend.background_manager(task, *args):
            status_code, headers = await self.receive_response(stream_id, timeout)
        content = self.body_iter(stream_id, timeout)
        on_close = functools.partial(self.response_closed, stream_id=stream_id)

        return AsyncResponse(
            status_code=status_code,
            http_version="HTTP/2",
            headers=headers,
            content=content,
            on_close=on_close,
            request=request,
        )

    async def close(self) -> None:
        await self.stream.close()

    def initiate_connection(self) -> None:
        self.h2_state.initiate_connection()
        data_to_send = self.h2_state.data_to_send()
        self.stream.write_no_block(data_to_send)
        self.initialized = True

    async def send_headers(
        self, request: AsyncRequest, timeout: TimeoutConfig = None
    ) -> int:
        stream_id = self.h2_state.get_next_available_stream_id()
        headers = [
            (b":method", request.method.encode("ascii")),
            (b":authority", request.url.authority.encode("ascii")),
            (b":scheme", request.url.scheme.encode("ascii")),
            (b":path", request.url.full_path.encode("ascii")),
        ] + [(k, v) for k, v in request.headers.raw if k != b"host"]

        logger.debug(
            f"send_headers "
            f"stream_id={stream_id} "
            f"method={request.method!r} "
            f"target={request.url.full_path!r} "
            f"headers={headers!r}"
        )

        self.h2_state.send_headers(stream_id, headers)
        data_to_send = self.h2_state.data_to_send()
        await self.stream.write(data_to_send, timeout)
        return stream_id

    async def send_request_data(
        self,
        stream_id: int,
        stream: typing.AsyncIterator[bytes],
        timeout: TimeoutConfig = None,
    ) -> None:
        try:
            async for data in stream:
                await self.send_data(stream_id, data, timeout)
            await self.end_stream(stream_id, timeout)
        finally:
            # Once we've sent the request we should enable read timeouts.
            self.timeout_flags[stream_id].set_read_timeouts()

    async def send_data(
        self, stream_id: int, data: bytes, timeout: TimeoutConfig = None
    ) -> None:
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
                await self.stream.write(data_to_send, timeout)

    async def end_stream(self, stream_id: int, timeout: TimeoutConfig = None) -> None:
        logger.debug(f"end_stream stream_id={stream_id}")
        self.h2_state.end_stream(stream_id)
        data_to_send = self.h2_state.data_to_send()
        await self.stream.write(data_to_send, timeout)

    async def receive_response(
        self, stream_id: int, timeout: TimeoutConfig = None
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
        self, stream_id: int, timeout: TimeoutConfig = None
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

    async def receive_event(
        self, stream_id: int, timeout: TimeoutConfig = None
    ) -> h2.events.Event:
        while not self.events[stream_id]:
            flag = self.timeout_flags[stream_id]
            data = await self.stream.read(self.READ_NUM_BYTES, timeout, flag=flag)
            events = self.h2_state.receive_data(data)
            for event in events:
                event_stream_id = getattr(event, "stream_id", 0)
                logger.debug(
                    f"receive_event stream_id={event_stream_id} event={event!r}"
                )
                if isinstance(event, h2.events.WindowUpdated):
                    if event_stream_id == 0:
                        for window_update_event in self.window_update_received.values():
                            window_update_event.set()
                    else:
                        try:
                            self.window_update_received[event_stream_id].set()
                        except KeyError:
                            # the window_update_received dictionary is only relevant
                            # when sending data, which should never raise a KeyError
                            # here.
                            pass

                if event_stream_id:
                    self.events[event.stream_id].append(event)

            data_to_send = self.h2_state.data_to_send()
            await self.stream.write(data_to_send, timeout)

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
        return self.stream.is_connection_dropped()
