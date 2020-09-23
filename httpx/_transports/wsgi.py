import io
import itertools
import typing

import httpcore


def _skip_leading_empty_chunks(body: typing.Iterable) -> typing.Iterable:
    body = iter(body)
    for chunk in body:
        if chunk:
            return itertools.chain([chunk], body)
    return []


class WSGITransport(httpcore.SyncHTTPTransport):
    """
    A custom transport that handles sending requests directly to an WSGI app.
    The simplest way to use this functionality is to use the `app` argument.

    ```
    client = httpx.Client(app=app)
    ```

    Alternatively, you can setup the transport instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the WSGITransport class:

    ```
    transport = httpx.WSGITransport(
        app=app,
        script_name="/submount",
        remote_addr="1.2.3.4"
    )
    client = httpx.Client(transport=transport)
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

    def request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        ext: dict = None,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], httpcore.SyncByteStream, dict
    ]:
        headers = [] if headers is None else headers
        stream = httpcore.PlainByteStream(content=b"") if stream is None else stream

        scheme, host, port, full_path = url
        path, _, query = full_path.partition(b"?")
        environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": scheme.decode("ascii"),
            "wsgi.input": io.BytesIO(b"".join(stream)),
            "wsgi.errors": io.BytesIO(),
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "REQUEST_METHOD": method.decode(),
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": path.decode("ascii"),
            "QUERY_STRING": query.decode("ascii"),
            "SERVER_NAME": host.decode("ascii"),
            "SERVER_PORT": str(port),
            "REMOTE_ADDR": self.remote_addr,
        }
        for header_key, header_value in headers:
            key = header_key.decode("ascii").upper().replace("-", "_")
            if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                key = "HTTP_" + key
            environ[key] = header_value.decode("ascii")

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
        # This is needed because the status returned by start_response
        # shouldn't be used until the first non-empty chunk has been served.
        result = _skip_leading_empty_chunks(result)

        assert seen_status is not None
        assert seen_response_headers is not None
        if seen_exc_info and self.raise_app_exceptions:
            raise seen_exc_info[1]

        status_code = int(seen_status.split()[0])
        headers = [
            (key.encode("ascii"), value.encode("ascii"))
            for key, value in seen_response_headers
        ]
        stream = httpcore.IteratorByteStream(iterator=result)
        ext = {}

        return (status_code, headers, stream, ext)
