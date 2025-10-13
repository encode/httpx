import contextlib
import logging
import time

from ._content import Text
from ._parsers import HTTPParser
from ._request import Request
from ._response import Response
from ._network import NetworkBackend, sleep
from ._streams import HTTPStream

__all__ = [
    "serve_http", "run"
]

logger = logging.getLogger("httpx.server")


class ConnectionClosed(Exception):
    pass


class HTTPConnection:
    def __init__(self, stream, endpoint):
        self._stream = stream
        self._endpoint = endpoint
        self._parser = HTTPParser(stream, mode='SERVER')
        self._keepalive_duration = 5.0
        self._idle_expiry = time.monotonic() + self._keepalive_duration

    # API entry points...
    async def handle_requests(self):
        try:
            while not self._parser.is_closed():
                if not await self._parser.wait_ready():
                    # Wait until we have read data, or return
                    # if the stream closes.
                    return
                # Read the initial part of the request,
                # and setup a stream for reading the body.
                method, url, headers = await self._recv_head()
                stream = HTTPStream(self._recv_body, self._reset)
                async with Request(method, url, headers=headers, content=stream) as request:
                    try:
                        response = await self._endpoint(request)
                        status_line = f"{request.method} {request.url.target} [{response.status_code} {response.reason_phrase}]"
                        logger.info(status_line)
                    except Exception:
                        logger.error("Internal Server Error", exc_info=True)
                        content = Text("Internal Server Error")
                        err = Response(500, content=content)
                        await self._send_head(err)
                        await self._send_body(err)
                    else:
                        await self._send_head(response)
                        await self._send_body(response)
                if self._parser.is_keepalive():
                    # If the client hasn't read the request body to
                    # completion, then do that here.
                    await stream.read()
                # Either revert to idle, or close the connection.
                await self._reset()
        except Exception:
            logger.error("Internal Server Error", exc_info=True)

    async def close(self):
        self._parser.close()

    # Receive the request...
    async def _recv_head(self) -> tuple[str, str, list[tuple[str, str]]]:
        method, target, _ = await self._parser.recv_method_line()
        m = method.decode('ascii')
        t = target.decode('ascii')
        headers = await self._parser.recv_headers()
        h = [
            (k.decode('latin-1'), v.decode('latin-1'))
            for k, v in headers
        ]
        return m, t, h

    async def _recv_body(self):
        return await self._parser.recv_body()

    # Return the response...
    async def _send_head(self, response: Response):
        protocol = b"HTTP/1.1"
        status = response.status_code
        reason = response.reason_phrase.encode('ascii')
        await self._parser.send_status_line(protocol, status, reason)
        headers = [
            (k.encode('ascii'), v.encode('ascii'))
            for k, v in response.headers.items()
        ]
        await self._parser.send_headers(headers)

    async def _send_body(self, response: Response):
        while data := await response.stream.read(64 * 1024):
            await self._parser.send_body(data)
        await self._parser.send_body(b'')

    # Start it all over again...
    async def _reset(self):
        await self._parser.reset()
        self._idle_expiry = time.monotonic() + self._keepalive_duration


class HTTPServer:
    def __init__(self, host, port):
        self.url = f"http://{host}:{port}/"

    async def wait(self):
        while(True):
            await sleep(1)


@contextlib.asynccontextmanager
async def serve_http(endpoint):
    async def handler(stream):
        connection = HTTPConnection(stream, endpoint)
        await connection.handle_requests()

    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG
    )

    backend = NetworkBackend()
    async with await backend.serve("127.0.0.1", 8080, handler) as server:
        server = HTTPServer(server.host, server.port)
        logger.info(f"Serving on {server.url} (Press CTRL+C to quit)")
        yield server


async def run(app):
    async with await serve_http(app) as server:
        server.wait()
