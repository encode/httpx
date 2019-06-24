import asyncio
import typing

import h11

from ..config import DEFAULT_TIMEOUT_CONFIG, TimeoutConfig, TimeoutTypes
from ..exceptions import ConnectTimeout, ReadTimeout
from ..interfaces import BaseReader, BaseWriter
from ..models import AsyncRequest, AsyncResponse

H11Event = typing.Union[
    h11.Request,
    h11.Response,
    h11.InformationalResponse,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


# Callback signature: async def callback() -> None
# In practice the callback will be a functools partial, which binds
# the `ConnectionPool.release_connection(conn: HTTPConnection)` method.
OnReleaseCallback = typing.Callable[[], typing.Awaitable[None]]


class HTTP11Connection:
    READ_NUM_BYTES = 4096

    def __init__(
        self,
        reader: BaseReader,
        writer: BaseWriter,
        on_release: typing.Optional[OnReleaseCallback] = None,
    ):
        self.reader = reader
        self.writer = writer
        self.on_release = on_release
        self.h11_state = h11.Connection(our_role=h11.CLIENT)

    async def send(
        self, request: AsyncRequest, timeout: TimeoutTypes = None
    ) -> AsyncResponse:
        timeout = None if timeout is None else TimeoutConfig(timeout)

        await self._send_request(request, timeout)
        loop = asyncio.get_event_loop()
        self.sender_task = loop.create_task(
            self._send_request_data(request.stream(), timeout)
        )
        status_code, headers = await self._receive_response(timeout)
        content = self._receive_response_data(timeout)

        return AsyncResponse(
            status_code=status_code,
            protocol="HTTP/1.1",
            headers=headers,
            content=content,
            on_close=self.response_closed,
            request=request,
        )

    async def close(self) -> None:
        event = h11.ConnectionClosed()
        try:
            self.h11_state.send(event)
        except h11.LocalProtocolError as exc:  # pragma: no cover
            # Premature client disconnect
            pass
        await self.writer.close()

    async def _send_request(
        self, request: AsyncRequest, timeout: TimeoutConfig = None
    ) -> None:
        """
        Send the request method, URL, and headers to the network.
        """
        method = request.method.encode("ascii")
        target = request.url.full_path.encode("ascii")
        headers = request.headers.raw
        if "Host" not in request.headers:
            host = request.url.authority.encode("ascii")
            headers = [(b"host", host)] + headers
        event = h11.Request(method=method, target=target, headers=headers)
        await self._send_event(event, timeout)

    async def _send_request_data(
        self, data: typing.AsyncIterator[bytes], timeout: TimeoutConfig = None
    ) -> None:
        """
        Send the request body to the network.
        """
        try:
            # Send the request body.
            async for chunk in data:
                event = h11.Data(data=chunk)
                await self._send_event(event, timeout)

            # Finalize sending the request.
            event = h11.EndOfMessage()
            await self._send_event(event, timeout)
        except OSError:  # pragma: nocover
            # We don't actually care about connection errors when sending the
            # request body. Defer to exceptions in the response, if any.
            pass

    async def _send_event(self, event: H11Event, timeout: TimeoutConfig = None) -> None:
        """
        Send a single `h11` event to the network, waiting for the data to
        drain before returning.
        """
        bytes_to_send = self.h11_state.send(event)
        await self.writer.write(bytes_to_send, timeout)

    async def _receive_response(
        self, timeout: TimeoutConfig = None
    ) -> typing.Tuple[int, typing.List[typing.Tuple[bytes, bytes]]]:
        """
        Read the response status and headers from the network.
        """
        while True:
            event = await self._recieve_event(timeout)
            if isinstance(event, h11.InformationalResponse):
                continue
            else:
                assert isinstance(event, h11.Response)
                break
        return (event.status_code, event.headers)

    async def _receive_response_data(
        self, timeout: TimeoutConfig = None
    ) -> typing.AsyncIterator[bytes]:
        """
        Read the response data from the network.
        """
        while True:
            event = await self._recieve_event(timeout)
            if isinstance(event, h11.Data):
                yield event.data
            else:
                assert isinstance(event, h11.EndOfMessage)
                break

    async def _recieve_event(self, timeout: TimeoutConfig = None) -> H11Event:
        """
        Read a single `h11` event, reading more data from the network if needed.
        """
        while True:
            event = self.h11_state.next_event()
            if event is h11.NEED_DATA:
                try:
                    data = await self.reader.read(self.READ_NUM_BYTES, timeout)
                except OSError:  # pragma: nocover
                    data = b""
                self.h11_state.receive_data(data)
            else:
                break
        return event

    async def response_closed(self) -> None:
        await self.sender_task
        self.sender_task.result()

        if (
            self.h11_state.our_state is h11.DONE
            and self.h11_state.their_state is h11.DONE
        ):
            self.h11_state.start_next_cycle()
        else:
            await self.close()

        if self.on_release is not None:
            await self.on_release()

    @property
    def is_closed(self) -> bool:
        return self.h11_state.our_state in (h11.CLOSED, h11.ERROR)
