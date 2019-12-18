import binascii
import mimetypes
import os
import typing
from io import BytesIO
from json import dumps as json_dumps
from pathlib import Path
from urllib.parse import urlencode

from .utils import format_form_param

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


class Stream:
    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b""

    async def aclose(self) -> None:
        pass


class AsyncIteratorStream(Stream):
    def __init__(self, iterator: typing.AsyncIterator[bytes], close: typing.Callable):
        self.iterator = iterator
        self.close_func = close

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for chunk in self.iterator:
            yield chunk

    async def aclose(self) -> None:
        await self.close_func()


class RequestStream(Stream):
    """
    Base class for streaming request content.
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


class BytesRequestStream(RequestStream):
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


class IteratorRequestStream(RequestStream):
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


class JSONRequestStream(RequestStream):
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


class URLEncodedRequestStream(RequestStream):
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


class MultipartRequestStream(RequestStream):
    """
    Request content as multipart encoded form data.
    """

    class DataField:
        """
        A single form field item, within a multipart form field.
        """

        def __init__(self, name: str, value: typing.Union[str, bytes]) -> None:
            if not isinstance(name, str):
                raise TypeError("Invalid type for name. Expected str.")
            if not isinstance(value, (str, bytes)):
                raise TypeError("Invalid type for value. Expected str or bytes.")
            self.name = name
            self.value = value

        def render_headers(self) -> bytes:
            name = format_form_param("name", self.name)
            return b"".join([b"Content-Disposition: form-data; ", name, b"\r\n\r\n"])

        def render_data(self) -> bytes:
            return (
                self.value
                if isinstance(self.value, bytes)
                else self.value.encode("utf-8")
            )

    class FileField:
        """
        A single file field item, within a multipart form field.
        """

        def __init__(
            self, name: str, value: typing.Union[typing.IO[typing.AnyStr], tuple]
        ) -> None:
            self.name = name
            if not isinstance(value, tuple):
                self.filename = Path(str(getattr(value, "name", "upload"))).name
                self.file = (
                    value
                )  # type: typing.Union[typing.IO[str], typing.IO[bytes]]
                self.content_type = self.guess_content_type()
            else:
                self.filename = value[0]
                self.file = value[1]
                self.content_type = (
                    value[2] if len(value) > 2 else self.guess_content_type()
                )

        def guess_content_type(self) -> typing.Optional[str]:
            if self.filename:
                return (
                    mimetypes.guess_type(self.filename)[0] or "application/octet-stream"
                )
            else:
                return None

        def render_headers(self) -> bytes:
            parts = [
                b"Content-Disposition: form-data; ",
                format_form_param("name", self.name),
            ]
            if self.filename:
                filename = format_form_param("filename", self.filename)
                parts.extend([b"; ", filename])
            if self.content_type is not None:
                content_type = self.content_type.encode()
                parts.extend([b"\r\nContent-Type: ", content_type])
            parts.append(b"\r\n\r\n")
            return b"".join(parts)

        def render_data(self) -> bytes:
            if isinstance(self.file, str):
                content = self.file
            else:
                content = self.file.read()
            return content.encode("utf-8") if isinstance(content, str) else content

    def __init__(self, data: dict, files: dict, boundary: bytes = None) -> None:
        body = BytesIO()
        if boundary is None:
            boundary = binascii.hexlify(os.urandom(16))

        for field in self.iter_fields(data, files):
            body.write(b"--%s\r\n" % boundary)
            body.write(field.render_headers())
            body.write(field.render_data())
            body.write(b"\r\n")

        body.write(b"--%s--\r\n" % boundary)

        self.content_type = "multipart/form-data; boundary=%s" % boundary.decode(
            "ascii"
        )
        self.body = body.getvalue()

    def iter_fields(
        self, data: dict, files: dict
    ) -> typing.Iterator[typing.Union["FileField", "DataField"]]:
        for name, value in data.items():
            if isinstance(value, (list, dict)):
                for item in value:
                    yield self.DataField(name=name, value=item)
            else:
                yield self.DataField(name=name, value=value)

        for name, value in files.items():
            yield self.FileField(name=name, value=value)

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
) -> RequestStream:
    """
    Handles encoding the given `data`, `files`, and `json`, returning
    a `RequestStream` implementation which provides a byte iterator onto
    the content, as well as `.is_rewindable()` and `.get_headers()` interfaces.

    The `boundary` argument is also included for reproducible test cases
    when working with multipart data.
    """
    if data is None:
        if json is not None:
            return JSONRequestStream(json)
        elif files:
            return MultipartRequestStream({}, files, boundary=boundary)
        else:
            return RequestStream()
    elif isinstance(data, dict):
        if files is not None:
            return MultipartRequestStream(data, files, boundary=boundary)
        else:
            return URLEncodedRequestStream(data)
    elif isinstance(data, (str, bytes)):
        return BytesRequestStream(data)
    else:
        return IteratorRequestStream(data)
