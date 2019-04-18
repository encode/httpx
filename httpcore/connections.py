import asyncio
import ssl
import typing

import h11

from .config import TimeoutConfig
from .datastructures import Request, Response
from .exceptions import ConnectTimeout, ReadTimeout

H11Event = typing.Union[
    h11.Request,
    h11.Response,
    h11.InformationalResponse,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


class Connection:
    def __init__(self, timeout: TimeoutConfig, on_release: typing.Callable = None):
        self.reader = None
        self.writer = None
        self.state = h11.Connection(our_role=h11.CLIENT)
        self.timeout = timeout
        self.on_release = on_release

    @property
    def is_closed(self) -> bool:
        return self.state.our_state in (h11.CLOSED, h11.ERROR)

    async def open(
        self, hostname: str, port: int, *, ssl: typing.Optional[ssl.SSLContext] = None
    ) -> None:
        try:
            self.reader, self.writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(hostname, port, ssl=ssl),
                self.timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

    async def send(self, request: Request) -> Response:
        method = request.method.encode()
        target = request.url.target
        headers = request.headers

        #  Start sending the request.
        event = h11.Request(method=method, target=target, headers=headers)
        await self._send_event(event)

        # Send the request body.
        if request.is_streaming:
            async for data in request.stream():
                event = h11.Data(data=data)
                await self._send_event(event)
        elif request.body:
            event = h11.Data(data=request.body)
            await self._send_event(event)

        # Finalize sending the request.
        event = h11.EndOfMessage()
        await self._send_event(event)

        # Start getting the response.
        event = await self._receive_event()
        if isinstance(event, h11.InformationalResponse):
            event = await self._receive_event()
        assert isinstance(event, h11.Response)
        reason = event.reason.decode('latin1')
        status_code = event.status_code
        headers = event.headers
        body = self._body_iter()
        return Response(
            status_code=status_code, reason=reason, headers=headers, body=body, on_close=self._release
        )

    async def _body_iter(self) -> typing.AsyncIterator[bytes]:
        event = await self._receive_event()
        while isinstance(event, h11.Data):
            yield event.data
            event = await self._receive_event()
        assert isinstance(event, h11.EndOfMessage)

    async def _send_event(self, event: H11Event) -> None:
        assert self.writer is not None

        data = self.state.send(event)
        self.writer.write(data)

    async def _receive_event(self) -> H11Event:
        assert self.reader is not None

        event = self.state.next_event()

        while event is h11.NEED_DATA:
            try:
                data = await asyncio.wait_for(
                    self.reader.read(2048), self.timeout.read_timeout
                )
            except asyncio.TimeoutError:
                raise ReadTimeout()
            self.state.receive_data(data)
            event = self.state.next_event()

        return event

    async def _release(self) -> None:
        assert self.writer is not None

        if self.state.our_state is h11.DONE and self.state.their_state is h11.DONE:
            self.state.start_next_cycle()
        else:
            self.close()

        if self.on_release is not None:
            await self.on_release(self)

    def close(self) -> None:
        assert self.writer is not None

        event = h11.ConnectionClosed()
        try:
            # If we're in h11.MUST_CLOSE then we'll end up in h11.CLOSED.
            self.state.send(event)
        except h11.ProtocolError:
            # If we're in some other state then it's a premature close,
            # and we'll end up in h11.ERROR.
            pass

        self.writer.close()
