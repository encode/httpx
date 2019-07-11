import codecs
import typing


def normalize_header_key(value: typing.AnyStr, encoding: str = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header key.
    """
    if isinstance(value, bytes):
        return value.lower()
    return value.encode(encoding or "ascii").lower()


def normalize_header_value(value: typing.AnyStr, encoding: str = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    return value.encode(encoding or "ascii")


def is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True


def get_content_length(
    value: typing.Union[typing.AnyStr, typing.IO[typing.AnyStr]]
) -> int:
    """
    Returns the size of str, bytes or a file-like object using tell() and seek()
    """
    if hasattr(value, "tell") and hasattr(value, "seek"):
        start = value.tell()
        value.seek(0, 2)
        end = value.tell()
        value.seek(start, 0)
        return end - start
    return len(value)


async def async_streamify(
    value: typing.Union[
        typing.AnyStr, typing.IO[typing.AnyStr], typing.Iterable[typing.AnyStr]
    ]
) -> typing.AsyncIterable[bytes]:
    """
    Turns raw data, a file-like object, or an iterable into an iterable of bytes.
    """
    if isinstance(value, bytes):
        yield value
    elif isinstance(value, str):
        yield value.encode("utf-8")
    elif hasattr(value, "read"):
        chunk = value.read(16384)
        while chunk:
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
            chunk = value.read(16384)
    elif hasattr(value, "__anext__"):
        while True:
            try:
                yield await value.__anext__()
            except StopAsyncIteration:
                break
    elif hasattr(value, "__aiter__"):
        async for chunk in value:
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
    else:
        for chunk in value:
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")


def streamify(
    value: typing.Union[
        typing.AnyStr, typing.IO[typing.AnyStr], typing.Iterable[typing.AnyStr]
    ]
) -> typing.Iterable[bytes]:
    """
    Turns raw data, a file-like object, or an iterable into an iterable of bytes.
    """
    if isinstance(value, bytes):
        yield value
    elif isinstance(value, str):
        yield value.encode("utf-8")
    elif hasattr(value, "read"):
        chunk = value.read(16384)
        while chunk:
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
            chunk = value.read(16384)
    else:
        for chunk in value:
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
