import io
import typing

from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import Dispatcher
from ..models import Request, Response


class WSGIDispatch(Dispatcher):
    def __init__(self, app: typing.Callable) -> None:
        self.app = app

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
            "wsgi.input": io.BytesIO(),
            "wsgi.errors": io.BytesIO(),
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": "",
            "PATH_INFO": request.url.path,
            "QUERY_STRING": request.url.query,
            "SERVER_NAME": request.url.host,
            "SERVER_PORT": str(request.url.port),
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

        return Response(
            status_code=int(seen_status.split()[0]),
            protocol="HTTP/1.1",
            headers=seen_response_headers,
            content=(chunk for chunk in result),
            on_close=getattr(result, "close", None),
        )
