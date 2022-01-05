import typing
from types import TracebackType

from .._models import Request, Response

T = typing.TypeVar("T", bound="BaseTransport")
A = typing.TypeVar("A", bound="AsyncBaseTransport")


class BaseTransport:
    def __enter__(self: T) -> T:
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()

    def handle_request(self, request: Request) -> Response:
        """
        Send a single HTTP request and return a response.

        At this layer of API we're simply using plain primitives. No `Request` or
        `Response` models, no fancy `URL` or `Header` handling. This strict point
        of cut-off provides a clear design separation between the HTTPX API,
        and the low-level network handling.

        Developers shouldn't typically ever need to call into this API directly,
        since the Client class provides all the higher level user-facing API
        niceties.

        In order to properly release any network resources, the response stream
        should *either* be consumed immediately, with a call to `stream.read()`,
        or else the `handle_request` call should be followed with a try/finally
        block to ensuring the stream is always closed.

        Example usage:

            with httpx.HTTPTransport() as transport:
                status_code, headers, stream, extensions = transport.handle_request(
                    method=b'GET',
                    url=(b'https', b'www.example.com', 443, b'/'),
                    headers=[(b'Host', b'www.example.com')],
                    stream=[],
                    extensions={}
                )
                body = stream.read()
                print(status_code, headers, body)

        Arguments:

        method: The request method as bytes. Eg. b'GET'.
        url: The components of the request URL, as a tuple of `(scheme, host, port, target)`.
             The target will usually be the URL path, but also allows for alternative
             formulations, such as proxy requests which include the complete URL in
             the target portion of the HTTP request, or for "OPTIONS *" requests, which
             cannot be expressed in a URL string.
        headers: The request headers as a list of byte pairs.
        stream: The request body as a bytes iterator.
        extensions: An open ended dictionary, including optional extensions to the
                    core request/response API. Keys may include:
            timeout: A dictionary of str:Optional[float] timeout values.
                     May include values for 'connect', 'read', 'write', or 'pool'.

        Returns a tuple of:

        status_code: The response status code as an integer. Should be in the range 1xx-5xx.
        headers: The response headers as a list of byte pairs.
        stream: The response body as a bytes iterator.
        extensions: An open ended dictionary, including optional extensions to the
                    core request/response API. Keys are plain strings, and may include:
            reason_phrase: The reason-phrase of the HTTP response, as bytes. Eg b'OK'.
                    HTTP/2 onwards does not include a reason phrase on the wire.
                    When no key is included, a default based on the status code may
                    be used. An empty-string reason phrase should not be substituted
                    for a default, as it indicates the server left the portion blank
                    eg. the leading response bytes were b"HTTP/1.1 200 <CRLF>".
            http_version: The HTTP version, as bytes. Eg. b"HTTP/1.1".
                    When no http_version key is included, HTTP/1.1 may be assumed.
        """
        raise NotImplementedError(
            "The 'handle_request' method must be implemented."
        )  # pragma: nocover

    def close(self) -> None:
        pass


class AsyncBaseTransport:
    async def __aenter__(self: A) -> A:
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.aclose()

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        raise NotImplementedError(
            "The 'handle_async_request' method must be implemented."
        )  # pragma: nocover

    async def aclose(self) -> None:
        pass
