import typing
from types import TracebackType

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

    def handle_request(
        self,
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: typing.Iterator[bytes],
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], typing.Iterator[bytes], dict
    ]:
        """
        Send a single HTTP request and return a response.

        At this layer of API we're simply using plain primitives. No `Request` or
        `Response` models, no fancy `URL` or `Header` handling. This strict point
        of cut-off provides a clear design seperation between the HTTPX API,
        and the low-level network handling.

        Developers shouldn't typically ever need to call into this API directly,
        since the Client class provides all the higher level user-facing API
        niceties.

        Example usage:

            with httpx.HTTPTransport() as transport:
                status_code, headers, stream, extensions = transport.handle_request(
                    method=b'GET',
                    url=(b'https', b'www.example.com', 443, b'/'),
                    headers=[(b'Host', b'www.example.com')],
                    stream=[],
                    extensions={}
                )
                try:
                    body = b''.join([part for part in stream])
                finally:
                    if 'close' in extensions:
                        extensions['close']()
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
            reason: The reason-phrase of the HTTP response, as bytes. Eg 'OK'.
                    HTTP/2 onwards does not include a reason phrase on the wire.
                    When no key is included, a default based on the status code may
                    be used. An empty-string reason phrase should not be substituted
                    for a default, as it indicates the server left the portion blank
                    eg. the leading response bytes were b"HTTP/1.1 200 <CRLF>".
            http_version: The HTTP version, as a string. Eg. "HTTP/1.1".
                    When no http_version key is included, "HTTP/1.1" may be assumed.
            close:  A callback which should be invoked to release any network
                    resources.
            aclose: An async callback which should be invoked to release any
                    network resources.
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
        method: bytes,
        url: typing.Tuple[bytes, bytes, typing.Optional[int], bytes],
        headers: typing.List[typing.Tuple[bytes, bytes]],
        stream: typing.AsyncIterator[bytes],
        extensions: dict,
    ) -> typing.Tuple[
        int, typing.List[typing.Tuple[bytes, bytes]], typing.AsyncIterator[bytes], dict
    ]:
        raise NotImplementedError(
            "The 'handle_async_request' method must be implemented."
        )  # pragma: nocover

    async def aclose(self) -> None:
        pass
