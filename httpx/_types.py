"""
Type definitions for type checking purposes.
"""

import ssl
from http.cookiejar import CookieJar
from typing import (
    IO,
    TYPE_CHECKING,
    AsyncIterable,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

if TYPE_CHECKING:  # pragma: no cover
    from ._auth import Auth  # noqa: F401
    from ._config import Proxy, Timeout  # noqa: F401
    from ._models import URL, Cookies, Headers, QueryParams, Request  # noqa: F401


PrimitiveData = Optional[Union[str, int, float, bool]]

RawURL = Tuple[bytes, bytes, Optional[int], bytes]

URLTypes = Union["URL", str]

QueryParamTypes = Union[
    "QueryParams",
    Mapping[str, Union[PrimitiveData, Sequence[PrimitiveData]]],
    List[Tuple[str, PrimitiveData]],
    str,
    bytes,
    None,
]

HeaderTypes = Union[
    "Headers",
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]

CookieTypes = Union["Cookies", CookieJar, Dict[str, str], List[Tuple[str, str]]]

CertTypes = Union[str, Tuple[str, str], Tuple[str, str, str]]
VerifyTypes = Union[str, bool, ssl.SSLContext]
TimeoutTypes = Union[
    Optional[float],
    Tuple[Optional[float], Optional[float], Optional[float], Optional[float]],
    "Timeout",
]
ProxiesTypes = Union[URLTypes, "Proxy", Dict[URLTypes, Union[None, URLTypes, "Proxy"]]]

AuthTypes = Union[
    Tuple[Union[str, bytes], Union[str, bytes]],
    Callable[["Request"], "Request"],
    "Auth",
    None,
]

ByteStream = Union[Iterable[bytes], AsyncIterable[bytes]]
RequestContent = Union[str, bytes, ByteStream]
ResponseContent = Union[str, bytes, ByteStream]

RequestData = dict

FileContent = Union[IO[str], IO[bytes], str, bytes]
FileTypes = Union[
    # file (or text)
    FileContent,
    # (filename, file (or text))
    Tuple[Optional[str], FileContent],
    # (filename, file (or text), content_type)
    Tuple[Optional[str], FileContent, Optional[str]],
]
RequestFiles = Union[Mapping[str, FileTypes], Sequence[Tuple[str, FileTypes]]]
