import functools
import typing

import h2.connection
import h2.events

from ..config import (
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    SSLConfig,
    TimeoutConfig,
)
from ..exceptions import ConnectTimeout, ReadTimeout
from ..interfaces import BaseReader, BaseWriter, Dispatcher
from ..models import Request, Response

OptionalTimeout = typing.Optional[TimeoutConfig]


class HTTP2Connection:
    READ_NUM_BYTES = 4096

    def __init__(
        self, reader: BaseReader, writer: BaseWriter, on_release: typing.Callable = None
    ):
        self.reader = reader
        self.writer = writer
        self.on_release = on_release
        self.h2_state = h2.connection.H2Connection()
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]
        self.initialized = False

    async def send(
        self, request: Request, stream: bool = False, timeout: TimeoutConfig = None
    ) -> Response:
        #  Start sending the request.
        if not self.initialized:
            self.initiate_connection()
        stream_id = await self.send_headers(request, timeout)
        self.events[stream_id] = []

        # Send the request body.
        async for data in request.stream():
            await self.send_data(stream_id, data, timeout)

        # Finalize sending the request.
        await self.end_stream(stream_id, timeout)

        # Start getting the response.
        while True:
            event = await self.receive_event(stream_id, timeout)
            if isinstance(event, h2.events.ResponseReceived):
                break

        status_code = 200
        headers = []
        for k, v in event.headers:
            if k == b":status":
                status_code = int(v.decode("ascii", errors="ignore"))
            elif not k.startswith(b":"):
                headers.append((k, v))

        content = self.body_iter(stream_id, timeout)
        on_close = functools.partial(self.response_closed, stream_id=stream_id)

        response = Response(
            status_code=status_code,
            protocol="HTTP/2",
            headers=headers,
            content=content,
            on_close=on_close,
            request=request,
        )

        if not stream:
            try:
                await response.read()
            finally:
                await response.close()

        return response

    async def close(self) -> None:
        await self.writer.close()

    def initiate_connection(self) -> None:
        self.h2_state.initiate_connection()
        data_to_send = self.h2_state.data_to_send()
        self.writer.write_no_block(data_to_send)
        self.initialized = True

    async def send_headers(self, request: Request, timeout: OptionalTimeout) -> int:
        stream_id = self.h2_state.get_next_available_stream_id()
        headers = [
            (b":method", request.method.encode("ascii")),
            (b":authority", request.url.authority.encode("ascii")),
            (b":scheme", request.url.scheme.encode("ascii")),
            (b":path", request.url.full_path.encode("ascii")),
        ] + request.headers.raw
        self.h2_state.send_headers(stream_id, headers)
        data_to_send = self.h2_state.data_to_send()
        await self.writer.write(data_to_send, timeout)
        return stream_id

    async def send_data(
        self, stream_id: int, data: bytes, timeout: OptionalTimeout
    ) -> None:
        self.h2_state.send_data(stream_id, data)
        data_to_send = self.h2_state.data_to_send()
        await self.writer.write(data_to_send, timeout)

    async def end_stream(self, stream_id: int, timeout: OptionalTimeout) -> None:
        self.h2_state.end_stream(stream_id)
        data_to_send = self.h2_state.data_to_send()
        await self.writer.write(data_to_send, timeout)

    async def body_iter(
        self, stream_id: int, timeout: OptionalTimeout
    ) -> typing.AsyncIterator[bytes]:
        while True:
            event = await self.receive_event(stream_id, timeout)
            if isinstance(event, h2.events.DataReceived):
                yield event.data
            elif isinstance(event, h2.events.StreamEnded):
                break

    async def receive_event(
        self, stream_id: int, timeout: OptionalTimeout
    ) -> h2.events.Event:
        while not self.events[stream_id]:
            data = await self.reader.read(self.READ_NUM_BYTES, timeout)
            events = self.h2_state.receive_data(data)
            for event in events:
                if getattr(event, "stream_id", 0):
                    self.events[event.stream_id].append(event)

            data_to_send = self.h2_state.data_to_send()
            await self.writer.write(data_to_send, timeout)

        return self.events[stream_id].pop(0)

    async def response_closed(self, stream_id: int) -> None:
        del self.events[stream_id]

        if not self.events and self.on_release is not None:
            await self.on_release()

    @property
    def is_closed(self) -> bool:
        return False
