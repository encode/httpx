import codecs
import collections
import contextlib
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

from ._exceptions import NetworkError

if typing.TYPE_CHECKING:  # pragma: no cover
    from ._models import PrimitiveData
    from ._models import URL


_HTML5_FORM_ENCODING_REPLACEMENTS = {'"': "%22", "\\": "\\\\"}
_HTML5_FORM_ENCODING_REPLACEMENTS.update(
    {chr(c): "%{:02X}".format(c) for c in range(0x00, 0x1F + 1) if c != 0x1B}
)
_HTML5_FORM_ENCODING_RE = re.compile(
    r"|".join([re.escape(c) for c in _HTML5_FORM_ENCODING_REPLACEMENTS.keys()])
)


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


def str_query_param(value: "PrimitiveData") -> str:
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


def format_form_param(name: str, value: typing.Union[str, bytes]) -> bytes:
    """
    Encode a name/value pair within a multipart form.
    """
    if isinstance(value, bytes):
        value = value.decode()

    def replacer(match: typing.Match[str]) -> str:
        return _HTML5_FORM_ENCODING_REPLACEMENTS[match.group(0)]

    value = _HTML5_FORM_ENCODING_RE.sub(replacer, value)
    return f'{name}="{value}"'.encode()


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


class NetRCInfo:
    def __init__(self, files: typing.Optional[typing.List[str]] = None) -> None:
        if files is None:
            files = [os.getenv("NETRC", ""), "~/.netrc", "~/_netrc"]
        self.netrc_files = files

    @property
    def netrc_info(self) -> typing.Optional[netrc.netrc]:
        if not hasattr(self, "_netrc_info"):
            self._netrc_info = None
            for file_path in self.netrc_files:
                expanded_path = Path(file_path).expanduser()
                if expanded_path.is_file():
                    self._netrc_info = netrc.netrc(str(expanded_path))
                    break
        return self._netrc_info

    def get_credentials(
        self, authority: str
    ) -> typing.Optional[typing.Tuple[str, str]]:
        if self.netrc_info is None:
            return None

        auth_info = self.netrc_info.authenticators(authority)
        if auth_info is None or auth_info[2] is None:
            return None
        return (auth_info[0], auth_info[2])


def get_ca_bundle_from_env() -> typing.Optional[str]:
    if "SSL_CERT_FILE" in os.environ:
        ssl_file = Path(os.environ["SSL_CERT_FILE"])
        if ssl_file.is_file():
            return str(ssl_file)
    if "SSL_CERT_DIR" in os.environ:
        ssl_path = Path(os.environ["SSL_CERT_DIR"])
        if ssl_path.is_dir():
            return str(ssl_path)
    return None


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


SENSITIVE_HEADERS = {"authorization", "proxy-authorization"}


def obfuscate_sensitive_headers(
    items: typing.Iterable[typing.Tuple[typing.AnyStr, typing.AnyStr]]
) -> typing.Iterator[typing.Tuple[typing.AnyStr, typing.AnyStr]]:
    for k, v in items:
        if to_str(k.lower()) in SENSITIVE_HEADERS:
            v = to_bytes_or_str("[secure]", match_type_of=v)
        yield k, v


_LOGGER_INITIALIZED = False
TRACE_LOG_LEVEL = 5


class Logger(logging.Logger):
    # Stub for type checkers.
    def trace(self, message: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        ...  # pragma: nocover


def get_logger(name: str) -> Logger:
    """
    Get a `logging.Logger` instance, and optionally
    set up debug logging based on the HTTPX_LOG_LEVEL environment variable.
    """
    global _LOGGER_INITIALIZED

    if not _LOGGER_INITIALIZED:
        _LOGGER_INITIALIZED = True
        logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")

        log_level = os.environ.get("HTTPX_LOG_LEVEL", "").upper()
        if log_level in ("DEBUG", "TRACE"):
            logger = logging.getLogger("httpx")
            logger.setLevel(logging.DEBUG if log_level == "DEBUG" else TRACE_LOG_LEVEL)
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    fmt="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(handler)

    logger = logging.getLogger(name)

    def trace(message: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        logger.log(TRACE_LOG_LEVEL, message, *args, **kwargs)

    logger.trace = trace  # type: ignore

    return typing.cast(Logger, logger)


def should_not_be_proxied(url: "URL") -> bool:
    """ Return True if url should not be proxied,
    return False otherwise.
    """
    no_proxy = getproxies().get("no")
    if not no_proxy:
        return False
    no_proxy_list = [host.strip() for host in no_proxy.split(",")]
    for name in no_proxy_list:
        if name == "*":
            return True
        if name:
            name = name.lstrip(".")  # ignore leading dots
            name = re.escape(name)
            pattern = r"(.+\.)?%s$" % name
            if re.match(pattern, url.host, re.I) or re.match(
                pattern, url.authority, re.I
            ):
                return True
    return False


def get_environment_proxies() -> typing.Dict[str, str]:
    """Gets proxy information from the environment"""

    # urllib.request.getproxies() falls back on System
    # Registry and Config for proxies on Windows and macOS.
    # We don't want to propagate non-HTTP proxies into
    # our configuration such as 'TRAVIS_APT_PROXY'.
    supported_proxy_schemes = ("http", "https", "all")
    return {
        key: val
        for key, val in getproxies().items()
        if ("://" in key or key in supported_proxy_schemes)
    }


def to_bytes(value: typing.Union[str, bytes], encoding: str = "utf-8") -> bytes:
    return value.encode(encoding) if isinstance(value, str) else value


def to_str(value: typing.Union[str, bytes], encoding: str = "utf-8") -> str:
    return value if isinstance(value, str) else value.decode(encoding)


def to_bytes_or_str(value: str, match_type_of: typing.AnyStr) -> typing.AnyStr:
    return value if isinstance(match_type_of, str) else value.encode()


def unquote(value: str) -> str:
    return value[1:-1] if value[0] == value[-1] == '"' else value


def flatten_queryparams(
    queryparams: typing.Mapping[
        str, typing.Union["PrimitiveData", typing.Sequence["PrimitiveData"]]
    ]
) -> typing.List[typing.Tuple[str, "PrimitiveData"]]:
    """
    Convert a mapping of query params into a flat list of two-tuples
    representing each item.

    Example:
    >>> flatten_queryparams_values({"q": "httpx", "tag": ["python", "dev"]})
    [("q", "httpx), ("tag", "python"), ("tag", "dev")]
    """
    items = []

    for k, v in queryparams.items():
        if isinstance(v, collections.abc.Sequence) and not isinstance(v, (str, bytes)):
            for u in v:
                items.append((k, u))
        else:
            items.append((k, typing.cast("PrimitiveData", v)))

    return items


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


@contextlib.contextmanager
def as_network_error(*exception_classes: type) -> typing.Iterator[None]:
    try:
        yield
    except BaseException as exc:
        for cls in exception_classes:
            if isinstance(exc, cls):
                raise NetworkError(exc) from exc
        raise
