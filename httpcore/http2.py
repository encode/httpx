import asyncio
import typing

import h2.connection
import h2.events

from .config import DEFAULT_SSL_CONFIG, DEFAULT_TIMEOUT_CONFIG, SSLConfig, TimeoutConfig
from .exceptions import ConnectTimeout, ReadTimeout
from .models import Client, Origin, Request, Response


class HTTP2Connection(Client):
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        origin: Origin,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        on_release: typing.Callable = None,
    ):
        self.origin = origin
        self.reader = reader
        self.writer = writer
        self.timeout = timeout
        self.on_release = on_release
        self.h2_state = h2.connection.H2Connection()
        self.events = {}  # type: typing.Dict[int, typing.List[h2.events.Event]]
        self.initialized = False

    @property
    def is_closed(self) -> bool:
        return False

    async def send(
        self,
        request: Request,
        *,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None
    ) -> Response:
        if timeout is None:
            timeout = self.timeout

        if not self.initialized:
            self.initiate_connection()

        #  Start sending the request.
        stream_id = self.h2_state.get_next_available_stream_id()
        self.events[stream_id] = []
        await self.send_headers(stream_id, request)

        # Send the request body.
        async for data in request.stream():
            await self.send_data(stream_id, data)

        # Finalize sending the request.
        await self.end_stream(stream_id)

        # Start getting the response.
        while True:
            event = await self.receive_event(stream_id, timeout)
            if isinstance(event, h2.events.ResponseReceived):
                break

        status_code = 200
        headers = []
        for k, v in event.headers:
            if k == b":status":
                status_code = int(v.decode())
            elif not k.startswith(b":"):
                headers.append((k, v))

        body = self.body_iter(stream_id, timeout)
        return Response(
            status_code=status_code,
            protocol="HTTP/2",
            headers=headers,
            body=body,
            on_close=self.release,
        )

    def initiate_connection(self) -> None:
        self.h2_state.initiate_connection()
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)
        self.initialized = True

    async def send_headers(self, stream_id: int, request: Request) -> None:
        headers = [
            (b":method", request.method.encode()),
            (b":authority", request.url.hostname.encode()),
            (b":scheme", request.url.scheme.encode()),
            (b":path", request.url.full_path.encode()),
        ] + request.headers
        self.h2_state.send_headers(stream_id, headers)
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def send_data(self, stream_id: int, data: bytes) -> None:
        self.h2_state.send_data(stream_id, data)
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def end_stream(self, stream_id: int) -> None:
        self.h2_state.end_stream(stream_id)
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def body_iter(
        self, stream_id: int, timeout: TimeoutConfig
    ) -> typing.AsyncIterator[bytes]:
        while True:
            event = await self.receive_event(stream_id, timeout)
            if isinstance(event, h2.events.DataReceived):
                yield event.data
            elif isinstance(event, h2.events.StreamEnded):
                del self.events[stream_id]
                break

    async def receive_event(
        self, stream_id: int, timeout: TimeoutConfig
    ) -> h2.events.Event:
        while not self.events[stream_id]:
            try:
                data = await asyncio.wait_for(
                    self.reader.read(2048), timeout.read_timeout
                )
            except asyncio.TimeoutError:
                raise ReadTimeout()

            events = self.h2_state.receive_data(data)
            for event in events:
                if getattr(event, "stream_id", 0):
                    self.events[event.stream_id].append(event)

            data_to_send = self.h2_state.data_to_send()
            if data_to_send:
                self.writer.write(data_to_send)

        return self.events[stream_id].pop(0)

    async def release(self) -> None:
        if self.on_release is not None:
            await self.on_release(self)

    async def close(self) -> None:
        self.writer.close()
