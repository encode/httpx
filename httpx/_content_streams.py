import binascii
import os
import typing
from json import dumps as json_dumps
from pathlib import Path
from urllib.parse import urlencode

import httpcore

from ._exceptions import StreamConsumed
from ._types import FileContent, FileTypes, RequestData, RequestFiles
from ._utils import (
    format_form_param,
    guess_content_type,
    peek_filelike_length,
    to_bytes,
)


class ContentStream(httpcore.AsyncByteStream, httpcore.SyncByteStream):
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
    Request content as streaming multipart encoded form data.
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
            if not hasattr(self, "_headers"):
                name = format_form_param("name", self.name)
                self._headers = b"".join(
                    [b"Content-Disposition: form-data; ", name, b"\r\n\r\n"]
                )

            return self._headers

        def render_data(self) -> bytes:
            if not hasattr(self, "_data"):
                self._data = (
                    self.value
                    if isinstance(self.value, bytes)
                    else self.value.encode("utf-8")
                )

            return self._data

        def get_length(self) -> int:
            headers = self.render_headers()
            data = self.render_data()
            return len(headers) + len(data)

        def can_replay(self) -> bool:
            return True

        def render(self) -> typing.Iterator[bytes]:
            yield self.render_headers()
            yield self.render_data()

    class FileField:
        """
        A single file field item, within a multipart form field.
        """

        def __init__(self, name: str, value: FileTypes) -> None:
            self.name = name

            fileobj: FileContent

            if isinstance(value, tuple):
                try:
                    filename, fileobj, content_type = value  # type: ignore
                except ValueError:
                    filename, fileobj = value  # type: ignore
                    content_type = guess_content_type(filename)
            else:
                filename = Path(str(getattr(value, "name", "upload"))).name
                fileobj = value
                content_type = guess_content_type(filename)

            self.filename = filename
            self.file = fileobj
            self.content_type = content_type

        def get_length(self) -> int:
            headers = self.render_headers()

            if isinstance(self.file, (str, bytes)):
                return len(headers) + len(self.file)

            # Let's do our best not to read `file` into memory.
            try:
                file_length = peek_filelike_length(self.file)
            except OSError:
                # As a last resort, read file and cache contents for later.
                assert not hasattr(self, "_data")
                self._data = to_bytes(self.file.read())
                file_length = len(self._data)

            return len(headers) + file_length

        def render_headers(self) -> bytes:
            if not hasattr(self, "_headers"):
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
                self._headers = b"".join(parts)

            return self._headers

        def render_data(self) -> typing.Iterator[bytes]:
            if isinstance(self.file, (str, bytes)):
                yield to_bytes(self.file)
                return

            if hasattr(self, "_data"):
                # Already rendered.
                yield self._data
                return

            for chunk in self.file:
                yield to_bytes(chunk)

            # Get ready for the next replay, if possible.
            if self.can_replay():
                assert self.file.seekable()
                self.file.seek(0)

        def can_replay(self) -> bool:
            return True if isinstance(self.file, (str, bytes)) else self.file.seekable()

        def render(self) -> typing.Iterator[bytes]:
            yield self.render_headers()
            yield from self.render_data()

    def __init__(
        self, data: typing.Mapping, files: RequestFiles, boundary: bytes = None
    ) -> None:
        if boundary is None:
            boundary = binascii.hexlify(os.urandom(16))

        self.boundary = boundary
        self.content_type = "multipart/form-data; boundary=%s" % boundary.decode(
            "ascii"
        )
        self.fields = list(self._iter_fields(data, files))

    def _iter_fields(
        self, data: typing.Mapping, files: RequestFiles
    ) -> typing.Iterator[typing.Union["FileField", "DataField"]]:
        for name, value in data.items():
            if isinstance(value, list):
                for item in value:
                    yield self.DataField(name=name, value=item)
            else:
                yield self.DataField(name=name, value=value)

        for name, value in files.items():
            yield self.FileField(name=name, value=value)

    def iter_chunks(self) -> typing.Iterator[bytes]:
        for field in self.fields:
            yield b"--%s\r\n" % self.boundary
            yield from field.render()
            yield b"\r\n"
        yield b"--%s--\r\n" % self.boundary

    def iter_chunks_lengths(self) -> typing.Iterator[int]:
        boundary_length = len(self.boundary)
        # Follow closely what `.iter_chunks()` does.
        for field in self.fields:
            yield 2 + boundary_length + 2
            yield field.get_length()
            yield 2
        yield 2 + boundary_length + 4

    def get_content_length(self) -> int:
        return sum(self.iter_chunks_lengths())

    # Content stream interface.

    def can_replay(self) -> bool:
        return all(field.can_replay() for field in self.fields)

    def get_headers(self) -> typing.Dict[str, str]:
        content_length = str(self.get_content_length())
        content_type = self.content_type
        return {"Content-Length": content_length, "Content-Type": content_type}

    def __iter__(self) -> typing.Iterator[bytes]:
        for chunk in self.iter_chunks():
            yield chunk

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        for chunk in self.iter_chunks():
            yield chunk


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
    if not data:
        if json is not None:
            return JSONStream(json=json)
        elif files:
            return MultipartStream(data={}, files=files, boundary=boundary)
        else:
            return ByteStream(body=b"")
    elif isinstance(data, dict):
        if files:
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
