import asyncio
import typing

import h11

from .config import DEFAULT_SSL_CONFIG, DEFAULT_TIMEOUT_CONFIG, SSLConfig, TimeoutConfig
from .datastructures import Client, Origin, Request, Response
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
    def __init__(
        self,
        origin: typing.Union[str, Origin],
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        on_release: typing.Callable = None,
    ):
        self.origin = Origin(origin) if isinstance(origin, str) else origin
        self.ssl = ssl
        self.timeout = timeout
        self.on_release = on_release
        self._reader = None
        self._writer = None
        self._h11_state = h11.Connection(our_role=h11.CLIENT)

    @property
    def is_closed(self) -> bool:
        return self._h11_state.our_state in (h11.CLOSED, h11.ERROR)

    async def send(
        self,
        request: Request,
        *,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
        stream: bool = False,
    ) -> Response:
        assert request.url.origin == self.origin

        if ssl is None:
            ssl = self.ssl
        if timeout is None:
            timeout = self.timeout

        # Make the connection
        if self._reader is None:
            await self._connect(ssl, timeout)

        #  Start sending the request.
        method = request.method.encode()
        target = request.url.target
        headers = request.headers
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
        event = await self._receive_event(timeout)
        if isinstance(event, h11.InformationalResponse):
            event = await self._receive_event(timeout)
        assert isinstance(event, h11.Response)
        reason = event.reason.decode("latin1")
        status_code = event.status_code
        headers = event.headers
        body = self._body_iter(timeout)
        response = Response(
            status_code=status_code,
            reason=reason,
            headers=headers,
            body=body,
            on_close=self._release,
        )

        if not stream:
            # Read the response body.
            try:
                await response.read()
            finally:
                await response.close()

        return response

    async def _connect(self, ssl: SSLConfig, timeout: TimeoutConfig) -> None:
        ssl_context = await ssl.load_ssl_context() if self.origin.is_secure else None

        try:
            self._reader, self._writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(
                    self.origin.hostname, self.origin.port, ssl=ssl_context
                ),
                timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

    async def _body_iter(self, timeout: TimeoutConfig) -> typing.AsyncIterator[bytes]:
        event = await self._receive_event(timeout)
        while isinstance(event, h11.Data):
            yield event.data
            event = await self._receive_event(timeout)
        assert isinstance(event, h11.EndOfMessage)

    async def _send_event(self, event: H11Event) -> None:
        assert self._writer is not None

        data = self._h11_state.send(event)
        self._writer.write(data)

    async def _receive_event(self, timeout: TimeoutConfig) -> H11Event:
        assert self._reader is not None

        event = self._h11_state.next_event()

        while event is h11.NEED_DATA:
            try:
                data = await asyncio.wait_for(
                    self._reader.read(2048), timeout.read_timeout
                )
            except asyncio.TimeoutError:
                raise ReadTimeout()
            self._h11_state.receive_data(data)
            event = self._h11_state.next_event()

        return event

    async def _release(self) -> None:
        assert self._writer is not None

        if (
            self._h11_state.our_state is h11.DONE
            and self._h11_state.their_state is h11.DONE
        ):
            self._h11_state.start_next_cycle()
        else:
            await self.close()

        if self.on_release is not None:
            await self.on_release(self)

    async def close(self) -> None:
        event = h11.ConnectionClosed()
        try:
            # If we're in h11.MUST_CLOSE then we'll end up in h11.CLOSED.
            self._h11_state.send(event)
        except h11.ProtocolError:
            # If we're in some other state then it's a premature close,
            # and we'll end up in h11.ERROR.
            pass

        if self._writer is not None:
            self._writer.close()
