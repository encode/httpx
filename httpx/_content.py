import inspect
import typing
from json import dumps as json_dumps
from urllib.parse import urlencode

from ._exceptions import StreamConsumed
from ._multipart import MultipartStream
from ._types import (
    ByteStream,
    RequestContent,
    RequestData,
    RequestFiles,
    ResponseContent,
)


class PlainByteStream:
    """
    Request content encoded as plain bytes.
    """

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __iter__(self) -> typing.Iterator[bytes]:
        yield self._body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self._body


class GeneratorStream:
    """
    Request content encoded as plain bytes, using an byte generator.
    """

    def __init__(self, generator: typing.Iterable[bytes]) -> None:
        self._generator = generator
        self._is_stream_consumed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        if self._is_stream_consumed:
            raise StreamConsumed()

        self._is_stream_consumed = True
        for part in self._generator:
            yield part


class AsyncGeneratorStream:
    """
    Request content encoded as plain bytes, using an async byte iterator.
    """

    def __init__(self, agenerator: typing.AsyncIterable[bytes]) -> None:
        self._agenerator = agenerator
        self._is_stream_consumed = False

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        if self._is_stream_consumed:
            raise StreamConsumed()

        self._is_stream_consumed = True
        async for part in self._agenerator:
            yield part


def encode_content(
    content: typing.Union[str, bytes, ByteStream]
) -> typing.Tuple[typing.Dict[str, str], ByteStream]:
    if isinstance(content, (str, bytes)):
        body = content.encode("utf-8") if isinstance(content, str) else content
        content_length = str(len(body))
        headers = {"Content-Length": content_length} if body else {}
        stream = PlainByteStream(body)
        return headers, stream

    elif isinstance(content, (typing.Iterable, typing.AsyncIterable)):
        headers = {"Transfer-Encoding": "chunked"}

        # Generators should be wrapped in GeneratorStream/AsyncGeneratorStream
        # which will raise `StreamConsumed` if the stream is accessed more
        # than once. (Eg. Following HTTP 307 or HTTP 308 redirects.)
        if inspect.isgenerator(content):
            generator_stream = GeneratorStream(content)  # type: ignore
            return headers, generator_stream
        if inspect.isasyncgen(content):
            agenerator_stream = AsyncGeneratorStream(content)  # type: ignore
            return headers, agenerator_stream

        # Other iterables may be passed through as-is.
        return headers, content  # type: ignore

    raise TypeError(f"Unexpected type for 'content', {type(content)!r}")


def encode_urlencoded_data(
    data: dict,
) -> typing.Tuple[typing.Dict[str, str], ByteStream]:
    body = urlencode(data, doseq=True).encode("utf-8")
    content_length = str(len(body))
    content_type = "application/x-www-form-urlencoded"
    headers = {"Content-Length": content_length, "Content-Type": content_type}
    return headers, PlainByteStream(body)


def encode_multipart_data(
    data: dict, files: RequestFiles, boundary: bytes = None
) -> typing.Tuple[typing.Dict[str, str], ByteStream]:
    stream = MultipartStream(data=data, files=files, boundary=boundary)
    headers = stream.get_headers()
    return headers, stream


def encode_json(json: typing.Any) -> typing.Tuple[typing.Dict[str, str], ByteStream]:
    body = json_dumps(json).encode("utf-8")
    content_length = str(len(body))
    content_type = "application/json"
    headers = {"Content-Length": content_length, "Content-Type": content_type}
    return headers, PlainByteStream(body)


def encode_request(
    content: RequestContent = None,
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    boundary: bytes = None,
) -> typing.Tuple[typing.Dict[str, str], ByteStream]:
    """
    Handles encoding the given `content`, `data`, `files`, and `json`,
    returning a two-tuple of (<headers>, <stream>).
    """
    if data is not None and not isinstance(data, dict):
        # We prefer to seperate `content=<bytes|str|byte iterator|bytes aiterator>`
        # for raw request content, and `data=<form data>` for url encoded or
        # multipart form content.
        #
        # However for compat with requests, we *do* still support
        # `data=<bytes...>` usages. We deal with that case here, treating it
        # as if `content=<...>` had been supplied instead.
        return encode_content(data)

    if content is not None:
        return encode_content(content)
    elif files:
        return encode_multipart_data(data or {}, files, boundary)
    elif data:
        return encode_urlencoded_data(data)
    elif json is not None:
        return encode_json(json)

    return {}, PlainByteStream(b"")


def encode_response(
    content: ResponseContent = None,
) -> typing.Tuple[typing.Dict[str, str], ByteStream]:
    """
    Handles encoding the given `content`, returning a two-tuple of
    (<headers>, <stream>).
    """
    if content is not None:
        return encode_content(content)

    return {}, PlainByteStream(b"")
