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
    def __init__(self, timeout: TimeoutConfig):
        self.reader = None
        self.writer = None
        self.state = h11.Connection(our_role=h11.CLIENT)
        self.timeout = timeout

    async def open(
        self,
        hostname: str,
        port: int,
        *,
        ssl: typing.Union[bool, ssl.SSLContext] = False
    ) -> None:
        try:
            self.reader, self.writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(hostname, port, ssl=ssl),
                self.timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

    async def send(self, request: Request, stream: bool = False) -> Response:
        method = request.method.encode()
        target = request.url.target
        host_header = (b"host", request.url.netloc.encode("ascii"))
        if request.is_streaming:
            content_length = (b"transfer-encoding", b"chunked")
        else:
            content_length = (b"content-length", str(len(request.body)).encode())

        headers = [host_header, content_length] + request.headers

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
        status_code = event.status_code
        headers = event.headers

        if stream:
            body_iter = self.body_iter()
            return Response(status_code=status_code, headers=headers, body=body_iter)

        #  Get the response body.
        body = b""
        event = await self._receive_event()
        while isinstance(event, h11.Data):
            body += event.data
            event = await self._receive_event()
        assert isinstance(event, h11.EndOfMessage)
        await self.close()

        return Response(status_code=status_code, headers=headers, body=body)

    async def body_iter(self) -> typing.AsyncIterator[bytes]:
        event = await self._receive_event()
        while isinstance(event, h11.Data):
            yield event.data
            event = await self._receive_event()
        assert isinstance(event, h11.EndOfMessage)
        await self.close()

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

    async def close(self) -> None:
        if self.writer is not None:
            self.writer.close()
            if hasattr(self.writer, "wait_closed"):
                await self.writer.wait_closed()
