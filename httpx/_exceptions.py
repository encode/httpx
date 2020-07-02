import contextlib
import typing

import httpcore

if typing.TYPE_CHECKING:
    from ._models import Request, Response  # pragma: nocover


class HTTPError(Exception):
    """
    Base class for all HTTPX exceptions.
    """

    def __init__(
        self, *args: typing.Any, request: "Request" = None, response: "Response" = None
    ) -> None:
        super().__init__(*args)
        self._request = request or (response.request if response is not None else None)
        self.response = response

    @property
    def request(self) -> "Request":
        # NOTE: this property exists so that a `Request` is exposed to type
        # checkers, instead of `Optional[Request]`.
        assert self._request is not None  # Populated by the client.
        return self._request


# Timeout exceptions...


class TimeoutException(HTTPError):
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


class NetworkError(HTTPError):
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


class ProxyError(HTTPError):
    """
    An error occurred while proxying a request.
    """


class ProtocolError(HTTPError):
    """
    A protocol was violated by the server.
    """


# HTTP exceptions...


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


class InvalidURL(HTTPError):
    """
    URL was missing a hostname, or was not one of HTTP/HTTPS.
    """


class CookieConflict(HTTPError):
    """
    Attempted to lookup a cookie by name, but multiple cookies existed.
    """


@contextlib.contextmanager
def map_exceptions(
    mapping: typing.Mapping[typing.Type[Exception], typing.Type[Exception]]
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

        raise mapped_exc(exc) from None


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
