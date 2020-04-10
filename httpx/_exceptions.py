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

ConnectTimeout = httpcore.ConnectTimeout
ReadTimeout = httpcore.ReadTimeout
WriteTimeout = httpcore.WriteTimeout
PoolTimeout = httpcore.PoolTimeout


# Core networking exceptions...

NetworkError = httpcore.NetworkError
ReadError = httpcore.ReadError
WriteError = httpcore.WriteError
ConnectError = httpcore.ConnectError
CloseError = httpcore.CloseError


# Other transport exceptions...

ProxyError = httpcore.ProxyError
ProtocolError = httpcore.ProtocolError


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
