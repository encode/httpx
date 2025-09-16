import types
import typing

from ._content import Content
from ._headers import Headers
from ._pool import ConnectionPool, Transport
from ._request import Request
from ._response import Response
from ._streams import Stream
from ._urls import URL

__all__ = ["Client"]


class Client:
    def __init__(
        self,
        url: URL | str | None = None,
        headers: Headers | typing.Mapping[str, str] | None = None,
        transport: Transport | None = None,
    ):
        if url is None:
            url = ""
        if headers is None:
            headers = {"User-Agent": "dev"}
        if transport is None:
            transport = ConnectionPool()

        self.url = URL(url)
        self.headers = Headers(headers)
        self.transport = transport
        self.via = RedirectMiddleware(self.transport)

    def build_request(
        self,
        method: str,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Request:
        return Request(
            method=method,
            url=self.url.join(url),
            headers=self.headers.copy_update(headers),
            content=content,
        )

    def request(
        self,
        method: str,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Response:
        request = self.build_request(method, url, headers=headers, content=content)
        with self.via.send(request) as response:
            response.read()
        return response

    def stream(
        self,
        method: str,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ) -> Response:
        request = self.build_request(method, url, headers=headers, content=content)
        return self.via.send(request)

    def get(
        self,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
    ):
        return self.request("GET", url, headers=headers)

    def post(
        self,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ):
        return self.request("POST", url, headers=headers, content=content)

    def put(
        self,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ):
        return self.request("PUT", url, headers=headers, content=content)

    def patch(
        self,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
        content: Content | Stream | bytes | None = None,
    ):
        return self.request("PATCH", url, headers=headers, content=content)

    def delete(
        self,
        url: URL | str,
        headers: Headers | typing.Mapping[str, str] | None = None,
    ):
        return self.request("DELETE", url, headers=headers)

    def close(self):
        self.transport.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None
    ):
        self.close()

    def __repr__(self):
        return f"<Client [{self.transport.description()}]>"


class RedirectMiddleware(Transport):
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def is_redirect(self, response: Response) -> bool:
        return (
            response.status_code in (301, 302, 303, 307, 308)
            and "Location" in response.headers
        )

    def build_redirect_request(self, request: Request, response: Response) -> Request:
        raise NotImplementedError()

    def send(self, request: Request) -> Response:
        while True:
            response = self._transport.send(request)

            if not self.is_redirect(response):
                return response

            # If we have a redirect, then we read the body of the response.
            # Ensures that the HTTP connection is available for a new
            # request/response cycle.
            response.read()
            response.close()

            # We've made a request-response and now need to issue a redirect request.
            request = self.build_redirect_request(request, response)

    def close(self):
        pass
