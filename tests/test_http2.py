import json

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
        request = self.requests[stream_id].pop(0)
        if not self.requests[stream_id]:
            del self.requests[stream_id]

        request_headers = dict(request["headers"])
        request_data = request["data"]

        response_body = json.dumps(
            {
                "method": request_headers[b":method"].decode(),
                "path": request_headers[b":path"].decode(),
                "body": request_data.decode(),
            }
        ).encode()

        response_headers = ((b":status", b"200"),)
        self.conn.send_headers(stream_id, response_headers)
        self.conn.send_data(stream_id, response_body, end_stream=True)
        self.buffer += self.conn.data_to_send()


@pytest.mark.asyncio
async def test_http2_get_request():
    server = MockServer()
    async with httpcore.HTTP2Connection(reader=server, writer=server) as conn:
        response = await conn.request("GET", "http://example.org")
    assert response.status_code == 200
    assert json.loads(response.body) == {"method": "GET", "path": "/", "body": ""}


@pytest.mark.asyncio
async def test_http2_post_request():
    server = MockServer()
    async with httpcore.HTTP2Connection(reader=server, writer=server) as conn:
        response = await conn.request("POST", "http://example.org", body=b"<data>")
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "method": "POST",
        "path": "/",
        "body": "<data>",
    }


@pytest.mark.asyncio
async def test_http2_multiple_requests():
    server = MockServer()
    async with httpcore.HTTP2Connection(reader=server, writer=server) as conn:
        response_1 = await conn.request("GET", "http://example.org/1")
        response_2 = await conn.request("GET", "http://example.org/2")
        response_3 = await conn.request("GET", "http://example.org/3")

    assert response_1.status_code == 200
    assert json.loads(response_1.body) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.body) == {"method": "GET", "path": "/2", "body": ""}

    assert response_3.status_code == 200
    assert json.loads(response_3.body) == {"method": "GET", "path": "/3", "body": ""}
