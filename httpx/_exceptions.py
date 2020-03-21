import typing

if typing.TYPE_CHECKING:
    from ._models import Request, Response  # pragma: nocover


class RequestError(Exception):
    """
    Base class for all httpx exceptions.
    """

    def __init__(
        self, *args: typing.Any, request: "Request" = None, response: "Response" = None
    ) -> None:
        self.response = response
        self.request = request or getattr(self.response, "request", None)
        super().__init__(*args)


HTTPError = RequestError  # For backward compatibility purposes.

# Timeout exceptions...


class TimeoutException(RequestError):
    """
    A base class for all timeouts.
    """


class ConnectTimeout(TimeoutException):
    """
    Timeout while establishing a connection.
    """


class ReadTimeout(TimeoutException):
    """
    Timeout while reading response data.
    """


class WriteTimeout(TimeoutException):
    """
    Timeout while writing request data.
    """


class PoolTimeout(TimeoutException):
    """
    Timeout while waiting to acquire a connection from the pool.
    """


class ProxyError(RequestError):
    """
    Error from within a proxy
    """


# HTTP exceptions...


class ProtocolError(RequestError):
    """
    Malformed HTTP.
    """


class DecodingError(RequestError):
    """
    Decoding of the response failed.
    """


class HTTPStatusError(RequestError):
    """
    HTTP Status Error.
    """


# Network exceptions...


class NetworkError(RequestError):
    """
    A failure occurred while trying to access the network.
    """


class ConnectionClosed(NetworkError):
    """
    Expected more data from peer, but connection was closed.
    """


# Redirect exceptions...


class RedirectError(RequestError):
    """
    Base class for HTTP redirect errors.
    """


class TooManyRedirects(RedirectError):
    """
    Too many redirects.
    """


class NotRedirectResponse(RedirectError):
    """
    Response was not a redirect response.
    """


# Stream exceptions...


class StreamError(RequestError):
    """
    The base class for stream exceptions.

    The developer made an error in accessing the request stream in
    an invalid way.
    """


class RequestBodyUnavailable(StreamError):
    """
    Had to send the request again, but the request body was streaming, and is
    no longer available.
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


class RequestNotRead(StreamError):
    """
    Attempted to access request content, without having called `read()`.
    """


class ResponseClosed(StreamError):
    """
    Attempted to read or stream response content, but the request has been
    closed.
    """


# Other cases...


class InvalidURL(RequestError):
    """
    URL was missing a hostname, or was not one of HTTP/HTTPS.
    """


class CookieConflict(RequestError):
    """
    Attempted to lookup a cookie by name, but multiple cookies existed.
    """
