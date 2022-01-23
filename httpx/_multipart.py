import binascii
import io
import os
import typing
from pathlib import Path

from ._types import (
    AsyncByteStream,
    FileContent,
    FileTypes,
    RequestFiles,
    SyncByteStream,
)
from ._utils import (
    format_form_param,
    guess_content_type,
    peek_filelike_length,
    primitive_value_to_str,
    to_bytes,
)


class DataField:
    """
    A single form field item, within a multipart form field.
    """

    def __init__(
        self, name: str, value: typing.Union[str, bytes, int, float, None]
    ) -> None:
        if not isinstance(name, str):
            raise TypeError(
                f"Invalid type for name. Expected str, got {type(name)}: {name!r}"
            )
        if value is not None and not isinstance(value, (str, bytes, int, float)):
            raise TypeError(
                f"Invalid type for value. Expected primitive type, got {type(value)}: {value!r}"
            )
        self.name = name
        self.value: typing.Union[str, bytes] = (
            value if isinstance(value, bytes) else primitive_value_to_str(value)
        )

    def render_headers(self) -> bytes:
        if not hasattr(self, "_headers"):
            name = format_form_param("name", self.name)
            self._headers = b"".join(
                [b"Content-Disposition: form-data; ", name, b"\r\n\r\n"]
            )

        return self._headers

    def render_data(self) -> bytes:
        if not hasattr(self, "_data"):
            self._data = to_bytes(self.value)

        return self._data

    def get_length(self) -> int:
        headers = self.render_headers()
        data = self.render_data()
        return len(headers) + len(data)

    def render(self) -> typing.Iterator[bytes]:
        yield self.render_headers()
        yield self.render_data()


class FileField:
    """
    A single file field item, within a multipart form field.
    """

    CHUNK_SIZE = 64 * 1024

    def __init__(self, name: str, value: FileTypes) -> None:
        self.name = name

        fileobj: FileContent

        headers: typing.Dict[str, str] = {}
        content_type: typing.Optional[str] = None

        # This large tuple based API largely mirror's requests' API
        # It would be good to think of better APIs for this that we could include in httpx 2.0
        # since variable length tuples (especially of 4 elements) are quite unwieldly
        if isinstance(value, tuple):
            if len(value) == 2:
                # neither the 3rd parameter (content_type) nor the 4th (headers) was included
                filename, fileobj = value  # type: ignore
            elif len(value) == 3:
                filename, fileobj, content_type = value  # type: ignore
            else:
                # all 4 parameters included
                filename, fileobj, content_type, headers = value  # type: ignore
        else:
            filename = Path(str(getattr(value, "name", "upload"))).name
            fileobj = value

        if content_type is None:
            content_type = guess_content_type(filename)

        has_content_type_header = any("content-type" in key.lower() for key in headers)
        if content_type is not None and not has_content_type_header:
            # note that unlike requests, we ignore the content_type
            # provided in the 3rd tuple element if it is also included in the headers
            # requests does the opposite (it overwrites the header with the 3rd tuple element)
            headers["Content-Type"] = content_type

        if isinstance(fileobj, (str, io.StringIO)):
            raise TypeError(f"Expected bytes or bytes-like object got: {type(fileobj)}")

        self.filename = filename
        self.file = fileobj
        self.headers = headers
        self._consumed = False

    def get_length(self) -> int:
        headers = self.render_headers()

        if isinstance(self.file, (str, bytes)):
            return len(headers) + len(to_bytes(self.file))

        # Let's do our best not to read `file` into memory.
        file_length = peek_filelike_length(self.file)
        if file_length is None:
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
            for header_name, header_value in self.headers.items():
                key, val = f"\r\n{header_name}: ".encode(), header_value.encode()
                parts.extend([key, val])
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

        if self._consumed:  # pragma: nocover
            self.file.seek(0)
        self._consumed = True

        chunk = self.file.read(self.CHUNK_SIZE)
        while chunk:
            yield to_bytes(chunk)
            chunk = self.file.read(self.CHUNK_SIZE)

    def render(self) -> typing.Iterator[bytes]:
        yield self.render_headers()
        yield from self.render_data()


class MultipartStream(SyncByteStream, AsyncByteStream):
    """
    Request content as streaming multipart encoded form data.
    """

    def __init__(self, data: dict, files: RequestFiles, boundary: bytes = None) -> None:
        if boundary is None:
            boundary = binascii.hexlify(os.urandom(16))

        self.boundary = boundary
        self.content_type = "multipart/form-data; boundary=%s" % boundary.decode(
            "ascii"
        )
        self.fields = list(self._iter_fields(data, files))

    def _iter_fields(
        self, data: dict, files: RequestFiles
    ) -> typing.Iterator[typing.Union[FileField, DataField]]:
        for name, value in data.items():
            if isinstance(value, list):
                for item in value:
                    yield DataField(name=name, value=item)
            else:
                yield DataField(name=name, value=value)

        file_items = files.items() if isinstance(files, typing.Mapping) else files
        for name, value in file_items:
            yield FileField(name=name, value=value)

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
