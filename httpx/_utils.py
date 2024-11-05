from __future__ import annotations

import codecs
import email.message
import mimetypes
import os
import re
import typing

from ._types import PrimitiveData

if typing.TYPE_CHECKING:  # pragma: no cover
    from ._urls import URL


_HTML5_FORM_ENCODING_REPLACEMENTS = {'"': "%22", "\\": "\\\\"}
_HTML5_FORM_ENCODING_REPLACEMENTS.update(
    {chr(c): "%{:02X}".format(c) for c in range(0x1F + 1) if c != 0x1B}
)
_HTML5_FORM_ENCODING_RE = re.compile(
    r"|".join([re.escape(c) for c in _HTML5_FORM_ENCODING_REPLACEMENTS.keys()])
)


def normalize_header_key(
    value: str | bytes,
    lower: bool,
    encoding: str | None = None,
) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header key.
    """
    if isinstance(value, bytes):
        bytes_value = value
    else:
        bytes_value = value.encode(encoding or "ascii")

    return bytes_value.lower() if lower else bytes_value


def normalize_header_value(value: str | bytes, encoding: str | None = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Header value must be str or bytes, not {type(value)}")
    return value.encode(encoding or "ascii")


def primitive_value_to_str(value: PrimitiveData) -> str:
    """
    Coerce a primitive data type into a string value.

    Note that we prefer JSON-style 'true'/'false' for boolean values here.
    """
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return ""
    return str(value)


def is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True


def format_form_param(name: str, value: str) -> bytes:
    """
    Encode a name/value pair within a multipart form.
    """

    def replacer(match: typing.Match[str]) -> str:
        return _HTML5_FORM_ENCODING_REPLACEMENTS[match.group(0)]

    value = _HTML5_FORM_ENCODING_RE.sub(replacer, value)
    return f'{name}="{value}"'.encode()


def parse_header_links(value: str) -> list[dict[str, str]]:
    """
    Returns a list of parsed link headers, for more info see:
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Link
    The generic syntax of those is:
    Link: < uri-reference >; param1=value1; param2="value2"
    So for instance:
    Link; '<http:/.../front.jpeg>; type="image/jpeg",<http://.../back.jpeg>;'
    would return
        [
            {"url": "http:/.../front.jpeg", "type": "image/jpeg"},
            {"url": "http://.../back.jpeg"},
        ]
    :param value: HTTP Link entity-header field
    :return: list of parsed link headers
    """
    links: list[dict[str, str]] = []
    replace_chars = " '\""
    value = value.strip(replace_chars)
    if not value:
        return links
    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""
        link = {"url": url.strip("<> '\"")}
        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break
            link[key.strip(replace_chars)] = value.strip(replace_chars)
        links.append(link)
    return links


def parse_content_type_charset(content_type: str) -> str | None:
    # We used to use `cgi.parse_header()` here, but `cgi` became a dead battery.
    # See: https://peps.python.org/pep-0594/#cgi
    msg = email.message.Message()
    msg["content-type"] = content_type
    return msg.get_content_charset(failobj=None)


SENSITIVE_HEADERS = {"authorization", "proxy-authorization"}


def obfuscate_sensitive_headers(
    items: typing.Iterable[tuple[typing.AnyStr, typing.AnyStr]],
) -> typing.Iterator[tuple[typing.AnyStr, typing.AnyStr]]:
    for k, v in items:
        if to_str(k.lower()) in SENSITIVE_HEADERS:
            v = to_bytes_or_str("[secure]", match_type_of=v)
        yield k, v


def port_or_default(url: URL) -> int | None:
    if url.port is not None:
        return url.port
    return {"http": 80, "https": 443}.get(url.scheme)


def same_origin(url: URL, other: URL) -> bool:
    """
    Return 'True' if the given URLs share the same origin.
    """
    return (
        url.scheme == other.scheme
        and url.host == other.host
        and port_or_default(url) == port_or_default(other)
    )


def is_https_redirect(url: URL, location: URL) -> bool:
    """
    Return 'True' if 'location' is a HTTPS upgrade of 'url'
    """
    if url.host != location.host:
        return False

    return (
        url.scheme == "http"
        and port_or_default(url) == 80
        and location.scheme == "https"
        and port_or_default(location) == 443
    )


def to_bytes(value: str | bytes, encoding: str = "utf-8") -> bytes:
    return value.encode(encoding) if isinstance(value, str) else value


def to_str(value: str | bytes, encoding: str = "utf-8") -> str:
    return value if isinstance(value, str) else value.decode(encoding)


def to_bytes_or_str(value: str, match_type_of: typing.AnyStr) -> typing.AnyStr:
    return value if isinstance(match_type_of, str) else value.encode()


def unquote(value: str) -> str:
    return value[1:-1] if value[0] == value[-1] == '"' else value


def guess_content_type(filename: str | None) -> str | None:
    if filename:
        return mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return None


def peek_filelike_length(stream: typing.Any) -> int | None:
    """
    Given a file-like stream object, return its length in number of bytes
    without reading it into memory.
    """
    try:
        # Is it an actual file?
        fd = stream.fileno()
        # Yup, seems to be an actual file.
        length = os.fstat(fd).st_size
    except (AttributeError, OSError):
        # No... Maybe it's something that supports random access, like `io.BytesIO`?
        try:
            # Assuming so, go to end of stream to figure out its length,
            # then put it back in place.
            offset = stream.tell()
            length = stream.seek(0, os.SEEK_END)
            stream.seek(offset)
        except (AttributeError, OSError):
            # Not even that? Sorry, we're doomed...
            return None

    return length
