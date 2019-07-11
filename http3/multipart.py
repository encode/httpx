import binascii
import mimetypes
import os
import typing
from urllib.parse import quote

from .utils import get_content_length


class Field:
    def render_headers(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def render_data(self) -> typing.Iterable[bytes]:
        raise NotImplementedError()  # pragma: nocover


class DataField(Field):
    __slots__ = ("name", "value")

    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value

    def render_headers(self) -> bytes:
        name = quote(self.name, encoding="utf-8").encode("ascii")
        return b"".join([b'Content-Disposition: form-data; name="', name, b'"\r\n\r\n'])

    def render_data(self) -> typing.Iterable[bytes]:
        yield self.value.encode("utf-8")


class FileField(Field):
    __slots__ = ("name", "value", "filename", "content_type")

    def __init__(
        self, name: str, value: typing.Union[typing.IO[typing.AnyStr], tuple]
    ) -> None:
        self.name = name
        if not isinstance(value, tuple):
            self.filename = os.path.basename(getattr(value, "name", "upload"))
            self.file = value  # type: typing.Union[typing.IO[typing.AnyStr]]
            self.content_type = self.guess_content_type()
        else:
            self.filename = value[0]
            self.file = value[1]
            self.content_type = (
                value[2] if len(value) > 2 else self.guess_content_type()
            )

    def guess_content_type(self) -> str:
        return mimetypes.guess_type(self.filename)[0] or "application/octet-stream"

    def render_headers(self) -> bytes:
        name = quote(self.name, encoding="utf-8").encode("ascii")
        filename = quote(self.filename, encoding="utf-8").encode("ascii")
        content_type = self.content_type.encode("ascii")
        return b"".join(
            [
                b'Content-Disposition: form-data; name="',
                name,
                b'"; filename="',
                filename,
                b'"\r\nContent-Type: ',
                content_type,
                b"\r\n\r\n",
            ]
        )

    def render_data(self) -> typing.Iterable[bytes]:
        chunk = self.file.read(16384)
        while chunk:
            yield chunk.encode("utf-8") if isinstance(chunk, str) else chunk
            chunk = self.file.read(16384)


def iter_fields(data: dict, files: dict) -> typing.Iterator[Field]:
    for name, value in data.items():
        if isinstance(value, list):
            for item in value:
                yield DataField(name=name, value=item)
        else:
            yield DataField(name=name, value=value)

    for name, value in files.items():
        yield FileField(name=name, value=value)


class _MultipartBody(object):
    def __init__(self, data: dict, files: dict, boundary: bytes):
        self._data = data
        self._files = files
        self._file_start_offset: typing.Dict[str, int] = {}
        self._boundary = boundary
        self._offset: int = 0
        self._size = None
        self._finished = False

        self._buffer = bytearray()
        self._generator = self._create_generator()

    def read(self, amount: int) -> bytes:
        if amount == 0 or self._finished:
            return b""
        data = self._buffer
        while len(data) < amount:
            try:
                data += next(self._generator)
            except StopIteration:
                break
        self._buffer = data[amount:]
        return bytes(data[:amount])

    def seek(self, offset: int, whence: int):
        if offset != 0 or whence not in (0, 2):  # pragma: nocover
            raise NotImplementedError(
                "MultipartBody only supports seek() to beginning and end"
            )
        if whence == 0:
            self._reset_generator()
        else:
            self._finished = True
            if self._size is None:
                self._size = (6 + len(self._boundary)) * (
                    len(self._data) + len(self._files) + 1
                )
                for field in iter_fields(self._data, {}):
                    self._size += len(field.render_headers()) + len(field.value)
                for field in iter_fields({}, self._files):
                    self._size += len(field.render_headers()) + get_content_length(
                        field.file
                    )
            self._offset = self._size
            print(self._size)

    def tell(self) -> int:
        return self._offset

    def _reset_generator(self):
        self._offset = 0
        self._finished = False
        for name, offset in self._file_start_offset.items():
            self._files[name].seek(offset, 0)
        self._generator = self._create_generator()

    def _create_generator(self):
        for field in iter_fields(self._data, self._files):
            yield b"--%s\r\n" % self._boundary
            yield field.render_headers()
            yield from field.render_data()
            yield b"\r\n"
        yield b"--%s--\r\n" % self._boundary


def multipart_encode(data: dict, files: dict) -> typing.Tuple[_MultipartBody, str]:
    boundary = binascii.hexlify(os.urandom(16))
    content_type = f"multipart/form-data; boundary={boundary.decode('ascii')}"
    return _MultipartBody(data, files, boundary), content_type
