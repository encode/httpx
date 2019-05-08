# Timeout exceptions...


class Timeout(Exception):
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


# HTTP exceptions...


class HttpError(Exception):
    """
    An Http error occurred.
    """


class ProtocolError(Exception):
    """
    Malformed HTTP.
    """


class DecodingError(Exception):
    """
    Decoding of the response failed.
    """


# Redirect exceptions...


class RedirectError(Exception):
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


# Stream exceptions...


class StreamException(Exception):
    """
    The base class for stream exceptions.

    The developer made an error in accessing the request stream in
    an invalid way.
    """


class StreamConsumed(StreamException):
    """
    Attempted to read or stream response content, but the content has already
    been streamed.
    """


class ResponseNotRead(StreamException):
    """
    Attempted to access response content, without having called `read()`
    after a streaming response.
    """


class ResponseClosed(StreamException):
    """
    Attempted to read or stream response content, but the request has been
    closed.
    """


# Other cases...


class InvalidURL(Exception):
    """
    URL was missing a hostname, or was not one of HTTP/HTTPS.
    """
