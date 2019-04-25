import h2.config
import h2.connection
import h2.events
import pytest

import httpcore


class MockServer(httpcore.BaseReader, httpcore.BaseWriter):
    """
    This class exposes Reader and Writer style interfaces
    """

    def __init__(self):
        config = h2.config.H2Configuration(client_side=False)
        self.conn = h2.connection.H2Connection(config=config)
        self.buffer = b""
        self.requests = {}

    # BaseReader interface

    async def read(self, n, timeout) -> bytes:
        send, self.buffer = self.buffer[:n], self.buffer[n:]
        return send

    # BaseWriter interface

    def write_no_block(self, data: bytes) -> None:
        events = self.conn.receive_data(data)
        self.buffer += self.conn.data_to_send()
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                self.request_received(event.headers, event.stream_id)
            elif isinstance(event, h2.events.DataReceived):
                self.receive_data(event.data, event.stream_id)
            elif isinstance(event, h2.events.StreamEnded):
                self.stream_complete(event.stream_id)

    async def write(self, data: bytes, timeout) -> None:
        self.write_no_block(data)

    async def close(self) -> None:
        pass

    # Server implementation

    def request_received(self, headers, stream_id):
        if stream_id not in self.requests:
            self.requests[stream_id] = []
        self.requests[stream_id].append({"headers": headers, "data": b""})

    def receive_data(self, data, stream_id):
        self.requests[stream_id][-1]["data"] += data

    def stream_complete(self, stream_id):
        requests = self.requests[stream_id].pop(0)
        if not self.requests[stream_id]:
            del self.requests[stream_id]

        response_headers = (
            (b":status", b"200"),
        )
        response_body = b"Hello, world!"
        self.conn.send_headers(stream_id, response_headers)
        self.conn.send_data(stream_id, response_body, end_stream=True)
        self.buffer += self.conn.data_to_send()


@pytest.mark.asyncio
async def test_http2():
    server = MockServer()
    origin = httpcore.Origin("http://example.org")
    client = httpcore.HTTP2Connection(reader=server, writer=server, origin=origin)
    response = await client.request("GET", "http://example.org")
    assert response.status_code == 200
    assert response.body == b"Hello, world!"
