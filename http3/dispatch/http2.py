import functools
import typing

import h2.connection
import h2.events

from ..concurrency import TimeoutFlag
from ..config import DEFAULT_TIMEOUT_CONFIG, TimeoutConfig, TimeoutTypes
from ..exceptions import ConnectTimeout, NotConnected, ReadTimeout
from ..interfaces import BaseReader, BaseWriter, ConcurrencyBackend
from ..models import AsyncRequest, AsyncResponse


class HTTP2Connection:
    READ_NUM_BYTES = 4096

    def __init__(
        self,
        reader: BaseReader,
        writer: BaseWriter,
        backend: ConcurrencyBackend,
        on_release: typing.Callable = None,
    ):
        self.reader = reader
        self.writer = writer
        self.backend = backend
        self.on_release = on_release
        self.h2_state = h2.connection.H2Connection()
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]
        self.timeout_flags = {}  # type: typing.Dict[int, TimeoutFlag]
        self.initialized = False

    async def send(
        self, request: AsyncRequest, timeout: TimeoutTypes = None
    ) -> AsyncResponse:
        timeout = None if timeout is None else TimeoutConfig(timeout)

        #  Start sending the request.
        if not self.initialized:
            self.initiate_connection()

        try:
            stream_id = await self.send_headers(request, timeout)
        except ConnectionResetError:
            raise NotConnected() from None

        self.events[stream_id] = []
        self.timeout_flags[stream_id] = TimeoutFlag()

        task, args = self.send_request_data, [stream_id, request.stream(), timeout]
        async with self.backend.background_manager(task, args=args):
            status_code, headers = await self.receive_response(stream_id, timeout)
        content = self.body_iter(stream_id, timeout)
        on_close = functools.partial(self.response_closed, stream_id=stream_id)

        return AsyncResponse(
            status_code=status_code,
            protocol="HTTP/2",
            headers=headers,
            content=content,
            on_close=on_close,
            request=request,
        )

    async def close(self) -> None:
        await self.writer.close()

    def initiate_connection(self) -> None:
        self.h2_state.initiate_connection()
        data_to_send = self.h2_state.data_to_send()
        self.writer.write_no_block(data_to_send)
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
        self.h2_state.send_headers(stream_id, headers)
        data_to_send = self.h2_state.data_to_send()
        await self.writer.write(data_to_send, timeout)
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
        flow_control = self.h2_state.local_flow_control_window(stream_id)
        chunk_size = min(len(data), flow_control)
        for idx in range(0, len(data), chunk_size):
            chunk = data[idx : idx + chunk_size]
            self.h2_state.send_data(stream_id, chunk)
            data_to_send = self.h2_state.data_to_send()
            await self.writer.write(data_to_send, timeout)

    async def end_stream(self, stream_id: int, timeout: TimeoutConfig = None) -> None:
        self.h2_state.end_stream(stream_id)
        data_to_send = self.h2_state.data_to_send()
        await self.writer.write(data_to_send, timeout)

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
                self.h2_state.acknowledge_received_data(len(event.data), stream_id)
                yield event.data
            elif isinstance(event, (h2.events.StreamEnded, h2.events.StreamReset)):
                break

    async def receive_event(
        self, stream_id: int, timeout: TimeoutConfig = None
    ) -> h2.events.Event:
        while not self.events[stream_id]:
            flag = self.timeout_flags[stream_id]
            data = await self.reader.read(self.READ_NUM_BYTES, timeout, flag=flag)
            events = self.h2_state.receive_data(data)
            for event in events:
                if getattr(event, "stream_id", 0):
                    self.events[event.stream_id].append(event)

            data_to_send = self.h2_state.data_to_send()
            await self.writer.write(data_to_send, timeout)

        return self.events[stream_id].pop(0)

    async def response_closed(self, stream_id: int) -> None:
        del self.events[stream_id]
        del self.timeout_flags[stream_id]

        if not self.events and self.on_release is not None:
            await self.on_release()

    @property
    def is_closed(self) -> bool:
        return False
