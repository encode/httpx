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


class PoolTimeout(Timeout):
    """
    Timeout while waiting to acquire a connection from the pool.
    """


class BadResponse(Exception):
    """
    A malformed HTTP response.
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
