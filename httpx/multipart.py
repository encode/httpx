import binascii
import mimetypes
import os
import re
import typing
from io import BytesIO
from pathlib import Path

_HTML5_FORM_ENCODING_REPLACEMENTS = {'"': "%22", "\\": "\\\\"}
_HTML5_FORM_ENCODING_REPLACEMENTS.update(
    {chr(c): "%{:02X}".format(c) for c in range(0x00, 0x1F + 1) if c != 0x1B}
)
_HTML5_FORM_ENCODING_RE = re.compile(
    r"|".join([re.escape(c) for c in _HTML5_FORM_ENCODING_REPLACEMENTS.keys()])
)


class Field:
    def render_headers(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def render_data(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover


class DataField(Field):
    def __init__(self, name: str, value: typing.Union[str, bytes]) -> None:
        if not isinstance(name, str):
            raise TypeError("Invalid type for name. Expected str.")
        if not isinstance(value, (str, bytes)):
            raise TypeError("Invalid type for value. Expected str or bytes.")
        self.name = name
        self.value = value

    def render_headers(self) -> bytes:
        name = _format_param("name", self.name)
        return b"".join([b"Content-Disposition: form-data; ", name, b"\r\n\r\n"])

    def render_data(self) -> bytes:
        return (
            self.value if isinstance(self.value, bytes) else self.value.encode("utf-8")
        )


class FileField(Field):
    def __init__(
        self, name: str, value: typing.Union[typing.IO[typing.AnyStr], tuple]
    ) -> None:
        self.name = name
        if not isinstance(value, tuple):
            self.filename = Path(str(getattr(value, "name", "upload"))).name
            self.file = value  # type: typing.Union[typing.IO[str], typing.IO[bytes]]
            self.content_type = self.guess_content_type()
        else:
            self.filename = value[0]
            self.file = value[1]
            self.content_type = (
                value[2] if len(value) > 2 else self.guess_content_type()
            )

    def guess_content_type(self) -> typing.Optional[str]:
        if self.filename:
            return mimetypes.guess_type(self.filename)[0] or "application/octet-stream"
        else:
            return None

    def render_headers(self) -> bytes:
        parts = [b"Content-Disposition: form-data; ", _format_param("name", self.name)]
        if self.filename:
            filename = _format_param("filename", self.filename)
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


def iter_fields(data: dict, files: dict) -> typing.Iterator[Field]:
    for name, value in data.items():
        if isinstance(value, (list, dict)):
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


def _format_param(name: str, value: typing.Union[str, bytes]) -> bytes:
    if isinstance(value, bytes):
        value = value.decode()

    def replacer(match: typing.Match[str]) -> str:
        return _HTML5_FORM_ENCODING_REPLACEMENTS[match.group(0)]

    value = _HTML5_FORM_ENCODING_RE.sub(replacer, value)
    return f'{name}="{value}"'.encode()
