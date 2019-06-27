import binascii
import mimetypes
import os
import typing
from io import BytesIO
from urllib.parse import quote


class Field:
    def render_headers(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def render_data(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover


class DataField(Field):
    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value

    def render_headers(self) -> bytes:
        name = quote(self.name, encoding="utf-8").encode("ascii")
        return b"".join(
            [b'Content-Disposition: form-data; name="', name, b'"\r\n' b"\r\n"]
        )

    def render_data(self) -> bytes:
        return self.value.encode("utf-8")


class FileField(Field):
    def __init__(
        self, name: str, value: typing.Union[typing.IO[typing.AnyStr], tuple]
    ) -> None:
        self.name = name
        if not isinstance(value, tuple):
            self.filename = os.path.basename(getattr(value, "name", "upload"))
            self.file = value  # type: typing.Union[typing.IO[str], typing.IO[bytes]]
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
                b'"\r\n',
                b"Content-Type: ",
                content_type,
                b"\r\n",
                b"\r\n",
            ]
        )

    def render_data(self) -> bytes:
        content = self.file.read()
        return content.encode("utf-8") if isinstance(content, str) else content


def iter_fields(data: dict, files: dict) -> typing.Iterator[Field]:
    for name, value in data.items():
        if isinstance(value, list):
            for item in value:
                yield DataField(name=name, value=item)
        else:
            yield DataField(name=name, value=value)

    for name, value in files.items():
        yield FileField(name=name, value=value)


def multipart_encode(data: dict, files: dict) -> typing.Tuple[bytes, str]:
    body = BytesIO()
    boundary = binascii.hexlify(os.urandom(16))

    for field in iter_fields(data, files):
        body.write(b"--%s\r\n" % boundary)
        body.write(field.render_headers())
        body.write(field.render_data())
        body.write(b"\r\n")

    body.write(b"--%s--\r\n" % boundary)

    content_type = "multipart/form-data; boundary=%s" % boundary.decode("ascii")

    return body.getvalue(), content_type
