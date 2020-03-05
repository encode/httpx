import binascii
import mimetypes
import os
import typing
from io import BytesIO
from json import dumps as json_dumps
from pathlib import Path
from urllib.parse import urlencode

from ._exceptions import StreamConsumed
from ._utils import format_form_param

RequestData = typing.Union[
    dict, str, bytes, typing.Iterator[bytes], typing.AsyncIterator[bytes]
]

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


class ContentStream:
    def get_headers(self) -> typing.Dict[str, str]:
        """
        Return a dictionary of headers that are implied by the encoding.
        """
        return {}

    def can_replay(self) -> bool:
        """
        Return `True` if `__aiter__` can be called multiple times.

        We need this in cases such determining if we can re-issue a request
        body when we receive a redirect response.
        """
        return True

    def __iter__(self) -> typing.Iterator[bytes]:
        yield b""

    def close(self) -> None:
        pass

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b""

    async def aclose(self) -> None:
        pass


class ByteStream(ContentStream):
    """
    Request content encoded as plain bytes.
    """

    def __init__(self, body: typing.Union[str, bytes]) -> None:
        self.body = body.encode("utf-8") if isinstance(body, str) else body

    def get_headers(self) -> typing.Dict[str, str]:
        if not self.body:
            return {}
        content_length = str(len(self.body))
        return {"Content-Length": content_length}

    def __iter__(self) -> typing.Iterator[bytes]:
        yield self.body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


class IteratorStream(ContentStream):
    """
    Request content encoded as plain bytes, using an byte iterator.
    """

    def __init__(
        self, iterator: typing.Iterator[bytes], close_func: typing.Callable = None
    ) -> None:
        self.iterator = iterator
        self.close_func = close_func
        self.is_stream_consumed = False

    def can_replay(self) -> bool:
        return False

    def get_headers(self) -> typing.Dict[str, str]:
        return {"Transfer-Encoding": "chunked"}

    def __iter__(self) -> typing.Iterator[bytes]:
        if self.is_stream_consumed:
            raise StreamConsumed()
        self.is_stream_consumed = True
        for part in self.iterator:
            yield part

    def __aiter__(self) -> typing.AsyncIterator[bytes]:
        raise RuntimeError("Attempted to call a async iterator on an sync stream.")

    def close(self) -> None:
        if self.close_func is not None:
            self.close_func()


class AsyncIteratorStream(ContentStream):
    """
    Request content encoded as plain bytes, using an async byte iterator.
    """

    def __init__(
        self, aiterator: typing.AsyncIterator[bytes], close_func: typing.Callable = None
    ) -> None:
        self.aiterator = aiterator
        self.close_func = close_func
        self.is_stream_consumed = False

    def can_replay(self) -> bool:
        return False

    def get_headers(self) -> typing.Dict[str, str]:
        return {"Transfer-Encoding": "chunked"}

    def __iter__(self) -> typing.Iterator[bytes]:
        raise RuntimeError("Attempted to call a sync iterator on an async stream.")

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        if self.is_stream_consumed:
            raise StreamConsumed()
        self.is_stream_consumed = True
        async for part in self.aiterator:
            yield part

    async def aclose(self) -> None:
        if self.close_func is not None:
            await self.close_func()


class JSONStream(ContentStream):
    """
    Request content encoded as JSON.
    """

    def __init__(self, json: typing.Any) -> None:
        self.body = json_dumps(json).encode("utf-8")

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(len(self.body))
        content_type = "application/json"
        return {"Content-Length": content_length, "Content-Type": content_type}

    def __iter__(self) -> typing.Iterator[bytes]:
        yield self.body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


class URLEncodedStream(ContentStream):
    """
    Request content as URL encoded form data.
    """

    def __init__(self, data: dict) -> None:
        self.body = urlencode(data, doseq=True).encode("utf-8")

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(len(self.body))
        content_type = "application/x-www-form-urlencoded"
        return {"Content-Length": content_length, "Content-Type": content_type}

    def __iter__(self) -> typing.Iterator[bytes]:
        yield self.body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


class MultipartStream(ContentStream):
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
            if isinstance(value, list):
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

    def __iter__(self) -> typing.Iterator[bytes]:
        yield self.body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self.body


def encode(
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    boundary: bytes = None,
) -> ContentStream:
    """
    Handles encoding the given `data`, `files`, and `json`, returning
    a `ContentStream` implementation.
    """
    if data is None:
        if json is not None:
            return JSONStream(json=json)
        elif files:
            return MultipartStream(data={}, files=files, boundary=boundary)
        else:
            return ByteStream(body=b"")
    elif isinstance(data, dict):
        if files is not None:
            return MultipartStream(data=data, files=files, boundary=boundary)
        else:
            return URLEncodedStream(data=data)
    elif isinstance(data, (str, bytes)):
        return ByteStream(body=data)
    elif hasattr(data, "__aiter__"):
        data = typing.cast(typing.AsyncIterator[bytes], data)
        return AsyncIteratorStream(aiterator=data)
    elif hasattr(data, "__iter__"):
        data = typing.cast(typing.Iterator[bytes], data)
        return IteratorStream(iterator=data)

    raise TypeError(f"Unexpected type for 'data', {type(data)!r}")
