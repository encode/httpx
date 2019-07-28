import binascii
import mimetypes
import os
import re
import typing
from io import BytesIO

_HTML5_REPLACEMENTS = {'"': "%22", "\\": "\\\\"}

_HTML5_REPLACEMENTS.update(
    {chr(cc): "%{:02X}".format(cc) for cc in range(0x00, 0x1F + 1) if cc not in (0x1B,)}
)


def _replace_multiple(
    value: str, needles_and_replacements: typing.Dict[str, str]
) -> str:
    def replacer(match: typing.Match[str]) -> str:
        return needles_and_replacements[match.group(0)]

    pattern = re.compile(
        r"|".join([re.escape(needle) for needle in needles_and_replacements.keys()])
    )

    result = pattern.sub(replacer, value)

    return result


def format_header_param_html5(name: str, value: typing.Union[str, bytes]) -> str:
    if isinstance(value, bytes):
        value = value.decode()

    value = _replace_multiple(value, _HTML5_REPLACEMENTS)

    return f'{name}="{value}"'


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
        name = format_header_param_html5("name", self.name).encode()
        return b"".join([b"Content-Disposition: form-data; ", name, b"\r\n", b"\r\n"])

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
        name = format_header_param_html5("name", self.name).encode()
        filename = format_header_param_html5("filename", self.filename).encode()
        content_type = self.content_type.encode()
        return b"".join(
            [
                b"Content-Disposition: form-data; ",
                name,
                b"; ",
                filename,
                b"\r\n",
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
