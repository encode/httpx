"""
Type definitions for type checking purposes.
"""

import ssl
from http.cookiejar import CookieJar
from typing import (
    IO,
    TYPE_CHECKING,
    AnyStr,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
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

StrOrBytes = Union[str, bytes]

PrimitiveData = Optional[Union[str, int, float, bool]]

URLTypes = Union["URL", str]

QueryParamTypes = Union[
    "QueryParams",
    Mapping[str, Union[PrimitiveData, Sequence[PrimitiveData]]],
    List[Tuple[str, PrimitiveData]],
    str,
]

HeaderTypes = Union[
    "Headers",
    # NOTE: Mapping is invariant in key (https://github.com/python/mypy/issues/1114).
    # So using `StrOrBytes` as the mapping key type would result in
    # users come across https://github.com/python/mypy/issues/8477.
    # The suggested solution is to use a generic key type (defined as a `TypeVar`),
    # hence `AnyStr` here.
    Mapping[AnyStr, StrOrBytes],
    Sequence[Tuple[StrOrBytes, StrOrBytes]],
]

CookieTypes = Union["Cookies", CookieJar, Dict[str, str]]

CertTypes = Union[str, Tuple[str, str], Tuple[str, str, str]]
VerifyTypes = Union[str, bool, ssl.SSLContext]
TimeoutTypes = Union[
    Optional[float],
    Tuple[Optional[float], Optional[float], Optional[float], Optional[float]],
    "Timeout",
]
ProxiesTypes = Union[URLTypes, "Proxy", Dict[URLTypes, Union[URLTypes, "Proxy"]]]

AuthTypes = Union[
    Tuple[Union[str, bytes], Union[str, bytes]],
    Callable[["Request"], "Request"],
    "Auth",
]

RequestData = Union[dict, str, bytes, Iterator[bytes], AsyncIterator[bytes]]

FileContent = Union[IO[str], IO[bytes], str, bytes]
FileTypes = Union[
    # file (or text)
    FileContent,
    # (filename, file (or text))
    Tuple[Optional[str], FileContent],
    # (filename, file (or text), content_type)
    Tuple[Optional[str], FileContent, Optional[str]],
]
RequestFiles = Mapping[str, FileTypes]
