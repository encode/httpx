import codecs
import logging
import netrc
import os
import re
import sys
import typing
from pathlib import Path


def normalize_header_key(value: typing.AnyStr, encoding: str = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header key.
    """
    if isinstance(value, bytes):
        return value.lower()
    return value.encode(encoding or "ascii").lower()


def normalize_header_value(value: typing.AnyStr, encoding: str = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    return value.encode(encoding or "ascii")


def str_query_param(value: typing.Optional[typing.Union[str, int, float, bool]]) -> str:
    """
    Coerce a primitive data type into a string value for query params.

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


# Null bytes; no need to recreate these on each call to guess_json_utf
_null = "\x00".encode("ascii")  # encoding to ASCII for Python 3
_null2 = _null * 2
_null3 = _null * 3


def guess_json_utf(data: bytes) -> typing.Optional[str]:
    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.
    sample = data[:4]
    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return "utf-32"  # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return "utf-8-sig"  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return "utf-16"  # BOM included
    nullcount = sample.count(_null)
    if nullcount == 0:
        return "utf-8"
    if nullcount == 2:
        if sample[::2] == _null2:  # 1st and 3rd are null
            return "utf-16-be"
        if sample[1::2] == _null2:  # 2nd and 4th are null
            return "utf-16-le"
        # Did not detect 2 valid UTF-16 ascii-range characters
    if nullcount == 3:
        if sample[:3] == _null3:
            return "utf-32-be"
        if sample[1:] == _null3:
            return "utf-32-le"
        # Did not detect a valid UTF-32 ascii-range character
    return None


NETRC_STATIC_FILES = (Path("~/.netrc"), Path("~/_netrc"))


def get_netrc_login(host: str) -> typing.Optional[typing.Tuple[str, str, str]]:
    NETRC_FILES = (Path(os.getenv("NETRC", "")),) + NETRC_STATIC_FILES
    netrc_path = None

    for file_path in NETRC_FILES:
        expanded_path = file_path.expanduser()
        if expanded_path.is_file():
            netrc_path = expanded_path
            break

    if netrc_path is None:
        return None

    netrc_info = netrc.netrc(str(netrc_path))
    return netrc_info.authenticators(host)  # type: ignore


def parse_header_links(value: str) -> typing.List[typing.Dict[str, str]]:
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
    links: typing.List[typing.Dict[str, str]] = []
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


_LOGGER_INITIALIZED = False


def get_logger(name: str) -> logging.Logger:
    """Gets a `logging.Logger` instance and optionally
    sets up debug logging if the user requests it via
    the `HTTPX_DEBUG=1` environment variable.
    """
    global _LOGGER_INITIALIZED

    if not _LOGGER_INITIALIZED:
        _LOGGER_INITIALIZED = True
        if os.environ.get("HTTPX_DEBUG", "").lower() in ("1", "true"):
            logger = logging.getLogger("httpx")
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s.%(msecs)03d - %(name)s - %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            logger.addHandler(handler)

    return logging.getLogger(name)


def to_bytes(str_or_bytes: typing.Union[str, bytes]) -> bytes:
    """Accepts an str or bytes object returning the bytes
    unmodified or the UTF-8 encoded string.
    """
    return (
        str_or_bytes.encode("utf-8") if isinstance(str_or_bytes, str) else str_or_bytes
    )


def to_str(str_or_bytes: typing.Union[str, bytes]) -> str:
    """Accepts an str or bytes object returning the str
    unmodified or the UTF-8 decoded string.
    """
    return (
        str_or_bytes if isinstance(str_or_bytes, str) else str_or_bytes.decode("utf-8")
    )


def unquote(value: str) -> str:
    """Remove quotes from a string if present."""
    return value[1:-1] if value[0] == value[-1] == '"' else value


class LRUDict(dict):
    """Subclass of dict keeping only the N last items inserted.

    When setting a new item the oldest element on the dict is deleted.
    """

    def __init__(
        self,
        max_size: int,
        *args: typing.Iterable[typing.Tuple[typing.Any, typing.Any]],
        **kwargs: typing.Any,
    ) -> None:
        if len(args) + len(kwargs) > max_size:
            raise ValueError("Cannot initialize with more elements than the maximum")
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            del self[list(self)[0]]


class DefaultLRUDict(LRUDict):
    def __init__(
        self,
        max_size: int,
        default_factory: typing.Callable = None,
        *args: typing.Iterable[typing.Tuple[typing.Any, typing.Any]],
        **kwargs: typing.Any,
    ) -> None:
        self.default_factory = default_factory
        super().__init__(max_size, *args, **kwargs)

    def __missing__(self, key: typing.Any) -> typing.Any:
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = self.default_factory()
        return self[key]
