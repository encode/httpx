"""
Our exception hierarchy:

* RequestError
  + TransportError
    - TimeoutException
      · ConnectTimeout
      · ReadTimeout
      · WriteTimeout
      · PoolTimeout
    - NetworkError
      · ConnectError
      · ReadError
      · WriteError
      · CloseError
    - ProxyError
    - ProtocolError
  + DecodingError
  + TooManyRedirects
  + RequestBodyUnavailable
  + InvalidURL
* HTTPStatusError
* NotRedirectResponse
* CookieConflict
* StreamError
  + StreamConsumed
  + ResponseNotRead
  + RequestNotRead
  + ResponseClosed
"""
import contextlib
import typing

import httpcore

if typing.TYPE_CHECKING:
    from ._models import Request, Response  # pragma: nocover


class RequestError(Exception):
    """
    Base class for all exceptions that may occur when issuing a `.request()`.
    """

    def __init__(self, message: str, *, request: "Request",) -> None:
        super().__init__(message)
        self.request = request


class TransportError(RequestError):
    """
    Base class for all exceptions that are mapped from the httpcore API.
    """


# Timeout exceptions...


class TimeoutException(TransportError):
    """
    The base class for timeout errors.

    An operation has timed out.
    """


class ConnectTimeout(TimeoutException):
    """
    Timed out while connecting to the host.
    """


class ReadTimeout(TimeoutException):
    """
    Timed out while receiving data from the host.
    """


class WriteTimeout(TimeoutException):
    """
    Timed out while sending data to the host.
    """


class PoolTimeout(TimeoutException):
    """
    Timed out waiting to acquire a connection from the pool.
    """


# Core networking exceptions...


class NetworkError(TransportError):
    """
    The base class for network-related errors.

    An error occurred while interacting with the network.
    """


class ReadError(NetworkError):
    """
    Failed to receive data from the network.
    """


class WriteError(NetworkError):
    """
    Failed to send data through the network.
    """


class ConnectError(NetworkError):
    """
    Failed to establish a connection.
    """


class CloseError(NetworkError):
    """
    Failed to close a connection.
    """


# Other transport exceptions...


class ProxyError(TransportError):
    """
    An error occurred while proxying a request.
    """


class ProtocolError(TransportError):
    """
    A protocol was violated by the server.
    """


# Other request exceptions...


class DecodingError(RequestError):
    """
    Decoding of the response failed.
    """


class TooManyRedirects(RequestError):
    """
    Too many redirects.
    """


class RequestBodyUnavailable(RequestError):
    """
    Had to send the request again, but the request body was streaming, and is
    no longer available.
    """


class InvalidURL(RequestError):
    """
    URL was missing a hostname, or was not one of HTTP/HTTPS.
    """


# Client errors


class HTTPStatusError(Exception):
    """
    Response sent an error HTTP status.

    May be raised when calling `response.raise_for_status()`
    """

    def __init__(
        self, message: str, *, request: "Request", response: "Response"
    ) -> None:
        super().__init__(message)
        self.request = request
        self.response = response


class NotRedirectResponse(Exception):
    """
    Response was not a redirect response.

    May be raised if `response.next()` is called without first
    properly checking `response.is_redirect`.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CookieConflict(Exception):
    """
    Attempted to lookup a cookie by name, but multiple cookies existed.

    Can occur when calling `response.cookies.get(...)`.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# Stream exceptions...

# These may occur as the result of a programming error, by accessing
# the request/response stream in an invalid manner.


class StreamError(Exception):
    """
    The base class for stream exceptions.

    The developer made an error in accessing the request stream in
    an invalid way.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class StreamConsumed(StreamError):
    """
    Attempted to read or stream response content, but the content has already
    been streamed.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to read or stream response content, but the content has "
            "already been streamed."
        )
        super().__init__(message)


class ResponseNotRead(StreamError):
    """
    Attempted to access response content, without having called `read()`
    after a streaming response.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to access response content, without having called `read()` "
            "after a streaming response."
        )
        super().__init__(message)


class RequestNotRead(StreamError):
    """
    Attempted to access request content, without having called `read()`.
    """

    def __init__(self) -> None:
        message = "Attempted to access request content, without having called `read()`."
        super().__init__(message)


class ResponseClosed(StreamError):
    """
    Attempted to read or stream response content, but the request has been
    closed.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to read or stream response content, but the request has "
            "been closed."
        )
        super().__init__(message)


# We're continuing to expose this earlier naming at the moment.
# It is due to be deprecated. Don't use it.
HTTPError = RequestError


@contextlib.contextmanager
def map_exceptions(
    mapping: typing.Mapping[typing.Type[Exception], typing.Type[Exception]],
    **kwargs: typing.Any,
) -> typing.Iterator[None]:
    try:
        yield
    except Exception as exc:
        mapped_exc = None

        for from_exc, to_exc in mapping.items():
            if not isinstance(exc, from_exc):
                continue
            # We want to map to the most specific exception we can find.
            # Eg if `exc` is an `httpcore.ReadTimeout`, we want to map to
            # `httpx.ReadTimeout`, not just `httpx.TimeoutException`.
            if mapped_exc is None or issubclass(to_exc, mapped_exc):
                mapped_exc = to_exc

        if mapped_exc is None:
            raise

        message = str(exc)
        raise mapped_exc(message, **kwargs) from None  # type: ignore


HTTPCORE_EXC_MAP = {
    httpcore.TimeoutException: TimeoutException,
    httpcore.ConnectTimeout: ConnectTimeout,
    httpcore.ReadTimeout: ReadTimeout,
    httpcore.WriteTimeout: WriteTimeout,
    httpcore.PoolTimeout: PoolTimeout,
    httpcore.NetworkError: NetworkError,
    httpcore.ConnectError: ConnectError,
    httpcore.ReadError: ReadError,
    httpcore.WriteError: WriteError,
    httpcore.CloseError: CloseError,
    httpcore.ProxyError: ProxyError,
    httpcore.ProtocolError: ProtocolError,
}
