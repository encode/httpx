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
    def handle_requests(self):
        try:
            while not self._parser.is_closed():
                method, url, headers = self._recv_head()
                stream = HTTPStream(self._recv_body, self._reset)
                # TODO: Handle endpoint exceptions
                with Request(method, url, headers=headers, content=stream) as request:
                    try:
                        response = self._endpoint(request)
                        status_line = f"{request.method} {request.url.target} [{response.status_code} {response.reason_phrase}]"
                        logger.info(status_line)
                    except Exception:
                        logger.error("Internal Server Error", exc_info=True)
                        content = Text("Internal Server Error")
                        err = Response(500, content=content)
                        self._send_head(err)
                        self._send_body(err)
                    else:
                        self._send_head(response)
                        self._send_body(response)
                if self._parser.is_keepalive():
                    stream.read()
                self._reset()
        except Exception:
            logger.error("Internal Server Error", exc_info=True)

    def close(self):
        self._parser.close()

    # Receive the request...
    def _recv_head(self) -> tuple[str, str, list[tuple[str, str]]]:
        method, target, _ = self._parser.recv_method_line()
        m = method.decode('ascii')
        t = target.decode('ascii')
        headers = self._parser.recv_headers()
        h = [
            (k.decode('latin-1'), v.decode('latin-1'))
            for k, v in headers
        ]
        return m, t, h

    def _recv_body(self):
        return self._parser.recv_body()

    # Return the response...
    def _send_head(self, response: Response):
        protocol = b"HTTP/1.1"
        status = response.status_code
        reason = response.reason_phrase.encode('ascii')
        self._parser.send_status_line(protocol, status, reason)
        headers = [
            (k.encode('ascii'), v.encode('ascii'))
            for k, v in response.headers.items()
        ]
        self._parser.send_headers(headers)

    def _send_body(self, response: Response):
        while data := response.stream.read(64 * 1024):
            self._parser.send_body(data)
        self._parser.send_body(b'')

    # Start it all over again...
    def _reset(self):
        self._parser.reset()
        self._idle_expiry = time.monotonic() + self._keepalive_duration


class HTTPServer:
    def __init__(self, host, port):
        self.url = f"http://{host}:{port}/"

    def wait(self):
        while(True):
            try:
                sleep(1)
            except KeyboardInterrupt:
                break


@contextlib.contextmanager
def serve_http(endpoint):
    def handler(stream):
        connection = HTTPConnection(stream, endpoint)
        connection.handle_requests()

    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG
    )

    backend = NetworkBackend()
    with backend.serve("127.0.0.1", 8080, handler) as server:
        server = HTTPServer(server.host, server.port)
        logger.info(f"Serving on {server.url} (Press CTRL+C to quit)")
        yield server


def run(app):
    with serve_http(app) as server:
        server.wait()
