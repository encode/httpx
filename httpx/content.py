import typing
from json import dumps as json_dumps
from urllib.parse import urlencode

from .multipart import multipart_encode

RequestData = typing.Union[dict, str, bytes, typing.AsyncIterator[bytes]]

RequestFiles = typing.Dict[
    str,
    typing.Union[
        # file (or str)
        typing.Union[typing.IO[typing.AnyStr], typing.AnyStr],
        # (filename, file (or str))
        typing.Tuple[
            typing.Optional[str], typing.Union[typing.IO[typing.AnyStr], typing.AnyStr],
        ],
        # (filename, file (or str), content_type)
        typing.Tuple[
            typing.Optional[str],
            typing.Union[typing.IO[typing.AnyStr], typing.AnyStr],
            typing.Optional[str],
        ],
    ],
]


class RequestContent:
    """
    Base class for request content.
    Defaults to a "no request body" implementation.
    """

    def get_headers(self) -> typing.Dict[str, str]:
        """
        Return a dictionary of request headers that are implied by the encoding.
        """
        return {}

    def can_replay(self) -> bool:
        """
        Return `True` if `__aiter__` can be called multiple times.

        We need this in order to determine if we can re-issue a request body
        when we receive a redirect response.
        """
        return True

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b""

    async def aread(self) -> bytes:
        return b"".join([part async for part in self])


class BytesRequestContent(RequestContent):
    """
    Request content encoded as plain bytes.
    """

    def __init__(self, body: typing.Union[str, bytes]) -> None:
        self.body = body.encode("utf-8") if isinstance(body, str) else body

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(len(self.body))
        return {"Content-Length": content_length}

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


class StreamingRequestContent(RequestContent):
    """
    Request content encoded as plain bytes, using an async byte iterator.
    """

    def __init__(self, aiterator: typing.AsyncIterator[bytes]) -> None:
        self.aiterator = aiterator

    def can_replay(self) -> bool:
        return False

    def get_headers(self) -> typing.Dict[str, str]:
        return {"Transfer-Encoding": "chunked"}

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for part in self.aiterator:
            yield part


class JSONRequestContent(RequestContent):
    """
    Request content encoded as JSON.
    """

    def __init__(self, json: typing.Any) -> None:
        self.body = json_dumps(json).encode("utf-8")

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(len(self.body))
        content_type = "application/json"
        return {"Content-Length": content_length, "Content-Type": content_type}

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


class URLEncodedRequestContent(RequestContent):
    """
    Request content as URL encoded form data.
    """

    def __init__(self, data: dict) -> None:
        self.body = urlencode(data, doseq=True).encode("utf-8")

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(len(self.body))
        content_type = "application/x-www-form-urlencoded"
        return {"Content-Length": content_length, "Content-Type": content_type}

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


class MultipartRequestContent(RequestContent):
    """
    Request content as multipart encoded form data.
    """

    def __init__(self, data: dict, files: dict, boundary: bytes = None) -> None:
        self.body, self.content_type = multipart_encode(data, files, boundary)

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(len(self.body))
        content_type = self.content_type
        return {"Content-Length": content_length, "Content-Type": content_type}

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


def encode(
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    boundary: bytes = None,
) -> RequestContent:
    """
    Handles encoding the given `data`, `files`, and `json`, returning
    a `RequestContent` implementation which provides a byte iterator onto
    the content, as well as `.is_rewindable()` and `.get_headers()` interfaces.

    The `boundary` argument is also included for reproducible test cases
    when working with multipart data.
    """
    if data is None:
        if json is not None:
            return JSONRequestContent(json)
        elif files:
            return MultipartRequestContent({}, files, boundary=boundary)
        else:
            return RequestContent()
    elif isinstance(data, dict):
        if files is not None:
            return MultipartRequestContent(data, files, boundary=boundary)
        else:
            return URLEncodedRequestContent(data)
    elif isinstance(data, (str, bytes)):
        return BytesRequestContent(data)
    else:
        return StreamingRequestContent(data)
