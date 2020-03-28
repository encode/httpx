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
    from ._models import Request, URL, QueryParams, Cookies, Headers  # noqa: F401
    from ._config import Timeout, Proxy  # noqa: F401
    from ._auth import Auth  # noqa: F401


PrimitiveData = Optional[Union[str, int, float, bool]]

URLTypes = Union["URL", str]
HeaderTypes = Union[
    "Headers", Mapping[AnyStr, AnyStr], Sequence[Tuple[AnyStr, AnyStr]],
]
QueryParamTypes = Union[
    "QueryParams",
    Dict[str, Union[PrimitiveData, Sequence[PrimitiveData]]],
    List[Tuple[str, PrimitiveData]],
    str,
]
CookieTypes = Union["Cookies", CookieJar, Dict[str, str]]
AuthTypes = Union[
    Tuple[Union[str, bytes], Union[str, bytes]],
    Callable[["Request"], "Request"],
    "Auth",
]
CertTypes = Union[str, Tuple[str, str], Tuple[str, str, str]]
VerifyTypes = Union[str, bool, ssl.SSLContext]
TimeoutTypes = Union[None, float, Tuple[float, float, float, float], "Timeout"]
ProxiesTypes = Union[URLTypes, "Proxy", Mapping[URLTypes, Union[URLTypes, "Proxy"]]]

RequestFormData = Dict[str, Union[Union[str, bytes], List[Union[str, bytes]]]]
RequestData = Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], RequestFormData]

RequestFileContent = Union[str, bytes, IO[str], IO[bytes]]
RequestFile = Union[
    # file content
    RequestFileContent,
    # (filename, file content)
    Tuple[Optional[str], RequestFileContent],
    # (filename, file content, content_type)
    Tuple[Optional[str], RequestFileContent, Optional[str]],
]
RequestFiles = Mapping[str, RequestFile]
