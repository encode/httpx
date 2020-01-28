import io
import typing

from .._config import TimeoutTypes
from .._content_streams import IteratorStream
from .._models import Request, Response
from .base import SyncDispatcher


class WSGIDispatch(SyncDispatcher):
    """
    A custom SyncDispatcher that handles sending requests directly to an WSGI app.
    The simplest way to use this functionality is to use the `app` argument.

    ```
    client = httpx.Client(app=app)
    ```

    Alternatively, you can setup the dispatch instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the WSGIDispatch class:

    ```
    dispatch = httpx.WSGIDispatch(
        app=app,
        script_name="/submount",
        remote_addr="1.2.3.4"
    )
    client = httpx.Client(dispatch=dispatch)
    ```

    Arguments:

    * `app` - The ASGI application.
    * `raise_app_exceptions` - Boolean indicating if exceptions in the application
       should be raised. Default to `True`. Can be set to `False` for use cases
       such as testing the content of a client 500 response.
    * `script_name` - The root path on which the ASGI application should be mounted.
    * `remote_addr` - A string indicating the client IP of incoming requests.
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

    def send(self, request: Request, timeout: TimeoutTypes = None) -> Response:
        environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": request.url.scheme,
            "wsgi.input": io.BytesIO(request.read()),
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
            http_version="HTTP/1.1",
            headers=seen_response_headers,
            stream=IteratorStream(chunk for chunk in result),
            request=request,
        )
