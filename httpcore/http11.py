import asyncio
import typing

import h11

from .config import DEFAULT_SSL_CONFIG, DEFAULT_TIMEOUT_CONFIG, SSLConfig, TimeoutConfig
from .exceptions import ConnectTimeout, ReadTimeout
from .models import Client, Origin, Request, Response

H11Event = typing.Union[
    h11.Request,
    h11.Response,
    h11.InformationalResponse,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


class HTTP11Connection(Client):
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
        self.h11_state = h11.Connection(our_role=h11.CLIENT)

    @property
    def is_closed(self) -> bool:
        return self.h11_state.our_state in (h11.CLOSED, h11.ERROR)

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
        method = request.method.encode()
        target = request.url.full_path
        headers = request.headers
        event = h11.Request(method=method, target=target, headers=headers)
        await self._send_event(event)

        # Send the request body.
        async for data in request.stream():
            event = h11.Data(data=data)
            await self._send_event(event)

        # Finalize sending the request.
        event = h11.EndOfMessage()
        await self._send_event(event)

        # Start getting the response.
        event = await self._receive_event(timeout)
        if isinstance(event, h11.InformationalResponse):
            event = await self._receive_event(timeout)

        assert isinstance(event, h11.Response)
        reason = event.reason.decode("latin1")
        status_code = event.status_code
        headers = event.headers
        body = self._body_iter(timeout)

        return Response(
            status_code=status_code,
            reason=reason,
            protocol="HTTP/1.1",
            headers=headers,
            body=body,
            on_close=self._release,
        )

    async def _body_iter(self, timeout: TimeoutConfig) -> typing.AsyncIterator[bytes]:
        event = await self._receive_event(timeout)
        while isinstance(event, h11.Data):
            yield event.data
            event = await self._receive_event(timeout)
        assert isinstance(event, h11.EndOfMessage)

    async def _send_event(self, event: H11Event) -> None:
        data = self.h11_state.send(event)
        self.writer.write(data)

    async def _receive_event(self, timeout: TimeoutConfig) -> H11Event:
        event = self.h11_state.next_event()

        while event is h11.NEED_DATA:
            try:
                data = await asyncio.wait_for(
                    self.reader.read(2048), timeout.read_timeout
                )
            except asyncio.TimeoutError:
                raise ReadTimeout()
            self.h11_state.receive_data(data)
            event = self.h11_state.next_event()

        return event

    async def _release(self) -> None:
        if (
            self.h11_state.our_state is h11.DONE
            and self.h11_state.their_state is h11.DONE
        ):
            self.h11_state.start_next_cycle()
        else:
            await self.close()

        if self.on_release is not None:
            await self.on_release(self)

    async def close(self) -> None:
        event = h11.ConnectionClosed()
        try:
            # If we're in h11.MUST_CLOSE then we'll end up in h11.CLOSED.
            self.h11_state.send(event)
        except h11.ProtocolError:
            # If we're in some other state then it's a premature close,
            # and we'll end up in h11.ERROR.
            pass

        if self.writer is not None:
            self.writer.close()
