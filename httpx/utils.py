import codecs
import logging
import netrc
import os
import re
import sys
import typing
from datetime import timedelta
from pathlib import Path
from time import perf_counter
from types import TracebackType
from urllib.request import getproxies


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


def get_environment_proxies() -> typing.Dict[str, str]:
    """Gets proxy information from the environment"""

    # urllib.request.getproxies() falls back on System
    # Registry and Config for proxies on Windows and macOS.
    # We don't want to propagate non-HTTP proxies into
    # our configuration such as 'TRAVIS_APT_PROXY'.
    proxies = {
        key: val
        for key, val in getproxies().items()
        if ("://" in key or key in ("http", "https"))
    }

    # Favor lowercase environment variables over uppercase.
    all_proxy = get_environ_lower_and_upper("ALL_PROXY")
    if all_proxy is not None:
        proxies["all"] = all_proxy

    return proxies


def get_environ_lower_and_upper(key: str) -> typing.Optional[str]:
    """Gets a value from os.environ with both the lowercase and uppercase
    environment variable. Prioritizes the lowercase environment variable.
    """
    for key in (key.lower(), key.upper()):
        value = os.environ.get(key, None)
        if value is not None and isinstance(value, str):
            return value
    return None


def to_bytes(value: typing.Union[str, bytes], encoding: str = "utf-8") -> bytes:
    return value.encode(encoding) if isinstance(value, str) else value


def to_str(value: typing.Union[str, bytes], encoding: str = "utf-8") -> str:
    return value if isinstance(value, str) else value.decode(encoding)


def unquote(value: str) -> str:
    return value[1:-1] if value[0] == value[-1] == '"' else value


class ElapsedTimer:
    def __init__(self) -> None:
        self.start: float = perf_counter()
        self.end: typing.Optional[float] = None

    def __enter__(self) -> "ElapsedTimer":
        self.start = perf_counter()
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.end = perf_counter()

    @property
    def elapsed(self) -> timedelta:
        if self.end is None:
            return timedelta(seconds=perf_counter() - self.start)
        return timedelta(seconds=self.end - self.start)
