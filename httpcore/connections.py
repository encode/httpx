from config import TimeoutConfig

import asyncio
import h11
import ssl


class Connection:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.state = h11.Connection(our_role=h11.CLIENT)

    async def open(self, host: str, port: int, ssl: ssl.SSLContext):
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ssl), timeout
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

    async def send(self, request: Request) -> Response:
        method = request.method

        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query

        headers = [
            ("host", request.url.netloc)
        ] += request.headers

        # Send the request method, path/query, and headers.
        event = h11.Request(method=method, target=target, headers=headers)
        await self._send_event(event)

        # Send the request body.
        if request.is_streaming:
            async for data in request.raw():
                event = h11.Data(data=data)
                await self._send_event(event)
        else:
            event = h11.Data(data=request.body)
            await self._send_event(event)

        # Finalize sending the request.
        event = h11.EndOfMessage()
        await connection.send_event(event)

    async def _send_event(self, message):
        data = self.state.send(message)
        self.writer.write(data)

    async def _receive_event(self, timeout):
        event = self.state.next_event()

        while type(event) is h11.NEED_DATA:
            try:
                data = await asyncio.wait_for(self.reader.read(2048), timeout)
            except asyncio.TimeoutError:
                raise ReadTimeout()
            self.state.receive_data(data)
            event = self.state.next_event()

        return event

    async def close(self):
        self.writer.close()
        if hasattr(self.writer, "wait_closed"):
            await self.writer.wait_closed()
