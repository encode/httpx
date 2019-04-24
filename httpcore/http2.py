import asyncio
import typing

import h2.connection
import h2.events

from .config import DEFAULT_SSL_CONFIG, DEFAULT_TIMEOUT_CONFIG, SSLConfig, TimeoutConfig
from .datastructures import Client, Origin, Request, Response
from .exceptions import ConnectTimeout, ReadTimeout


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
        self.events = []  # type: typing.List[h2.events.Event]

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

        #  Start sending the request.
        await self._initiate_connection()
        await self._send_headers(request)

        # Send the request body.
        if request.body:
            await self._send_data(request.body)

        # Finalize sending the request.
        await self._end_stream()

        # Start getting the response.
        while True:
            event = await self._receive_event(timeout)
            if isinstance(event, h2.events.ResponseReceived):
                break

        status_code = 200
        headers = []
        for k, v in event.headers:
            if k == b":status":
                status_code = int(v.decode())
            elif not k.startswith(b":"):
                headers.append((k, v))

        body = self._body_iter(timeout)
        return Response(
            status_code=status_code,
            protocol="HTTP/2",
            headers=headers,
            body=body,
            on_close=self._release,
        )

    async def _initiate_connection(self) -> None:
        self.h2_state.initiate_connection()
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def _send_headers(self, request: Request) -> None:
        headers = [
            (b":method", request.method.encode()),
            (b":authority", request.url.hostname.encode()),
            (b":scheme", request.url.scheme.encode()),
            (b":path", request.url.full_path.encode()),
        ] + request.headers
        self.h2_state.send_headers(1, headers)
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def _send_data(self, data: bytes) -> None:
        self.h2_state.send_data(1, data)
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def _end_stream(self) -> None:
        self.h2_state.end_stream(1)
        data_to_send = self.h2_state.data_to_send()
        self.writer.write(data_to_send)

    async def _body_iter(self, timeout: TimeoutConfig) -> typing.AsyncIterator[bytes]:
        while True:
            event = await self._receive_event(timeout)
            if isinstance(event, h2.events.DataReceived):
                yield event.data
            elif isinstance(event, h2.events.StreamEnded):
                break

    async def _receive_event(self, timeout: TimeoutConfig) -> h2.events.Event:
        while not self.events:
            try:
                data = await asyncio.wait_for(
                    self.reader.read(2048), timeout.read_timeout
                )
            except asyncio.TimeoutError:
                raise ReadTimeout()

            events = self.h2_state.receive_data(data)
            self.events.extend(events)

            data_to_send = self.h2_state.data_to_send()
            if data_to_send:
                self.writer.write(data_to_send)

        return self.events.pop(0)

    async def _release(self) -> None:
        # if (
        #     self.h11_state.our_state is h11.DONE
        #     and self.h11_state.their_state is h11.DONE
        # ):
        #     self.h11_state.start_next_cycle()
        # else:
        #     await self.close()

        if self.on_release is not None:
            await self.on_release(self)

    async def close(self) -> None:
        # event = h11.ConnectionClosed()
        # try:
        #     # If we're in h11.MUST_CLOSE then we'll end up in h11.CLOSED.
        #     self.h11_state.send(event)
        # except h11.ProtocolError:
        #     # If we're in some other state then it's a premature close,
        #     # and we'll end up in h11.ERROR.
        #     pass

        if self.writer is not None:
            self.writer.close()
