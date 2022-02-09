"""
Type definitions for type checking purposes.
"""

import ssl
from http.cookiejar import CookieJar
from typing import (
    IO,
    TYPE_CHECKING,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
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


PrimitiveData = Optional[Union[str, int, float, bool]]

RawURL = Tuple[bytes, bytes, Optional[int], bytes]

URLTypes = Union["URL", str]

QueryParamTypes = Union[
    "QueryParams",
    Mapping[str, Union[PrimitiveData, Sequence[PrimitiveData]]],
    List[Tuple[str, PrimitiveData]],
    Tuple[Tuple[str, PrimitiveData], ...],
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

CertTypes = Union[
    # certfile
    str,
    # (certfile, keyfile)
    Tuple[str, Optional[str]],
    # (certfile, keyfile, password)
    Tuple[str, Optional[str], Optional[str]],
]
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

RequestContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]
ResponseContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]

RequestData = dict

FileContent = Union[IO[bytes], bytes]
FileTypes = Union[
    # file (or bytes)
    FileContent,
    # (filename, file (or bytes))
    Tuple[Optional[str], FileContent],
    # (filename, file (or bytes), content_type)
    Tuple[Optional[str], FileContent, Optional[str]],
    # (filename, file (or bytes), content_type, headers)
    Tuple[Optional[str], FileContent, Optional[str], Mapping[str, str]],
]
RequestFiles = Union[Mapping[str, FileTypes], Sequence[Tuple[str, FileTypes]]]


class SyncByteStream:
    def __iter__(self) -> Iterator[bytes]:
        raise NotImplementedError(
            "The '__iter__' method must be implemented."
        )  # pragma: nocover
        yield b""  # pragma: nocover

    def close(self) -> None:
        """
        Subclasses can override this method to release any network resources
        after a request/response cycle is complete.

        Streaming cases should use a `try...finally` block to ensure that
        the stream `close()` method is always called.

        Example:

            status_code, headers, stream, extensions = transport.handle_request(...)
            try:
                ...
            finally:
                stream.close()
        """

    def read(self) -> bytes:
        """
        Simple cases can use `.read()` as a convenience method for consuming
        the entire stream and then closing it.

        Example:

            status_code, headers, stream, extensions = transport.handle_request(...)
            body = stream.read()
        """
        try:
            return b"".join([part for part in self])
        finally:
            self.close()


class AsyncByteStream:
    async def __aiter__(self) -> AsyncIterator[bytes]:
        raise NotImplementedError(
            "The '__aiter__' method must be implemented."
        )  # pragma: nocover
        yield b""  # pragma: nocover

    async def aclose(self) -> None:
        pass

    async def aread(self) -> bytes:
        try:
            return b"".join([part async for part in self])
        finally:
            await self.aclose()
