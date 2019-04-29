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


class ProtocolError(Exception):
    """
    Malformed HTTP.
    """


class StreamConsumed(Exception):
    """
    Attempted to read or stream response content, but the content has already
    been streamed.
    """


class ResponseClosed(Exception):
    """
    Attempted to read or stream response content, but the request has been
    closed without loading the body.
    """


class DecodingError(Exception):
    """
    Decoding of the response failed.
    """


class InvalidURL(Exception):
    """
    URL was missing a hostname, or was not one of HTTP/HTTPS.
    """
