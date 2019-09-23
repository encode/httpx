import typing

if typing.TYPE_CHECKING:
    from .models import BaseRequest, BaseResponse  # pragma: nocover


class HTTPError(Exception):
    """
    Base class for Httpx exception
    """

    def __init__(
        self,
        *args: typing.Any,
        request: "BaseRequest" = None,
        response: "BaseResponse" = None,
    ) -> None:
        self.response = response
        self.request = request or getattr(self.response, "request", None)
        super().__init__(*args)


# Timeout exceptions...


class Timeout(HTTPError):
    """
    A base class for all timeouts.
    """


class ConnectTimeout(Timeout):
    """
    Timeout while establishing a connection.
    """


class ReadTimeout(Timeout):
    """
    Timeout while reading response data.
    """


class WriteTimeout(Timeout):
    """
    Timeout while writing request data.
    """


class PoolTimeout(Timeout):
    """
    Timeout while waiting to acquire a connection from the pool.
    """


class ProxyError(HTTPError):
    """
    Error from within a proxy
    """


# HTTP exceptions...


class ProtocolError(HTTPError):
    """
    Malformed HTTP.
    """


class DecodingError(HTTPError):
    """
    Decoding of the response failed.
    """


# Redirect exceptions...


class RedirectError(HTTPError):
    """
    Base class for HTTP redirect errors.
    """


class TooManyRedirects(RedirectError):
    """
    Too many redirects.
    """


class RedirectBodyUnavailable(RedirectError):
    """
    Got a redirect response, but the request body was streaming, and is
    no longer available.
    """


class RedirectLoop(RedirectError):
    """
    Infinite redirect loop.
    """


class NotRedirectResponse(RedirectError):
    """
    Response was not a redirect response.
    """


# Stream exceptions...


class StreamError(HTTPError):
    """
    The base class for stream exceptions.

    The developer made an error in accessing the request stream in
    an invalid way.
    """


class StreamConsumed(StreamError):
    """
    Attempted to read or stream response content, but the content has already
    been streamed.
    """


class ResponseNotRead(StreamError):
    """
    Attempted to access response content, without having called `read()`
    after a streaming response.
    """


class ResponseClosed(StreamError):
    """
    Attempted to read or stream response content, but the request has been
    closed.
    """


# Other cases...


class InvalidURL(HTTPError):
    """
    URL was missing a hostname, or was not one of HTTP/HTTPS.
    """


class CookieConflict(HTTPError):
    """
    Attempted to lookup a cookie by name, but multiple cookies existed.
    """
