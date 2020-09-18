import binascii
import os
import typing
from pathlib import Path

from ._types import FileContent, FileTypes, RequestFiles
from ._utils import (
    format_form_param,
    guess_content_type,
    peek_filelike_length,
    to_bytes,
)


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
        self._consumed = False

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

        if self._consumed:  # pragma: nocover
            self.file.seek(0)
        self._consumed = True

        for chunk in self.file:
            yield to_bytes(chunk)

    def render(self) -> typing.Iterator[bytes]:
        yield self.render_headers()
        yield from self.render_data()


class MultipartStream:
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
