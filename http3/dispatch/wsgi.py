import io
import typing

from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import Dispatcher
from ..models import Request, Response


class WSGIDispatch(Dispatcher):
    """
    A custom dispatcher that handles sending requests directly to an ASGI app.

    The simplest way to use this functionality is to use the `app`argument.
    This will automatically infer if 'app' is a WSGI or an ASGI application,
    and will setup an appropriate dispatch class:

    ```
    client = http3.Client(app=app)
    ```

    Alternatively, you can setup the dispatch instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the WSGIDispatch class:

    ```
    dispatch = http3.WSGIDispatch(
        app=app,
        script_name="/submount",
        remote_addr="1.2.3.4"
    )
    client = http3.Client(dispatch=dispatch)
    ```
    """

    def __init__(
        self,
        app: typing.Callable,
        raise_app_exceptions: bool = True,
        script_name: str = "",
        remote_addr: str = "127.0.0.1",
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.script_name = script_name
        self.remote_addr = remote_addr

    def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": request.url.scheme,
            "wsgi.input": BodyStream(request.stream()),
            "wsgi.errors": io.BytesIO(),
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": request.url.path,
            "QUERY_STRING": request.url.query,
            "SERVER_NAME": request.url.host,
            "SERVER_PORT": str(request.url.port),
            "REMOTE_ADDR": self.remote_addr,
        }
        for key, value in request.headers.items():
            key = key.upper().replace("-", "_")
            if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                key = "HTTP_" + key
            environ[key] = value

        seen_status = None
        seen_response_headers = None
        seen_exc_info = None

        def start_response(
            status: str, response_headers: list, exc_info: typing.Any = None
        ) -> None:
            nonlocal seen_status, seen_response_headers, seen_exc_info
            seen_status = status
            seen_response_headers = response_headers
            seen_exc_info = exc_info

        result = self.app(environ, start_response)

        assert seen_status is not None
        assert seen_response_headers is not None
        if seen_exc_info and self.raise_app_exceptions:
            raise seen_exc_info[1]

        return Response(
            status_code=int(seen_status.split()[0]),
            protocol="HTTP/1.1",
            headers=seen_response_headers,
            content=(chunk for chunk in result),
            on_close=getattr(result, "close", None),
        )


class BodyStream(io.RawIOBase):
    def __init__(self, iterator: typing.Iterator[bytes]) -> None:
        self._iterator = iterator
        self._buffer = b""
        self._closed = False

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            return b""

        if size == -1:
            return self.readall()

        try:
            while len(self._buffer) < size:
                self._buffer += next(self._iterator)
        except StopIteration:
            self._closed = True
            return self._buffer

        output = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return output

    def readall(self) -> bytes:
        if self._closed:
            raise OSError("Stream closed")  # pragma: nocover

        for chunk in self._iterator:
            self._buffer += chunk

        self._closed = True
        return self._buffer

    def readinto(self, b: bytearray) -> typing.Optional[int]:  # pragma: nocover
        output = self.read(len(b))
        count = len(output)
        b[:count] = output
        return count

    def write(self, b: bytes) -> int:
        raise OSError("Operation not supported")  # pragma: nocover

    def fileno(self) -> int:
        raise OSError("Operation not supported")  # pragma: nocover

    def seek(self, offset: int, whence: int = 0) -> int:
        raise OSError("Operation not supported")  # pragma: nocover

    def truncate(self, size: int = None) -> int:
        raise OSError("Operation not supported")  # pragma: nocover
