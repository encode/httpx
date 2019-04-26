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


class DeflateDecodingError(DecodingError):
    """
    Decoding of the response using deflate failed.
    """


class GzipDecodingError(DecodingError):
    """
    Decoding of the response using gzip failed.
    """


class BrotliDecodingError(DecodingError):
    """
    Decoding of the response using brotli failed.
    """
