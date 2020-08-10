from .__version__ import __description__, __title__, __version__
from ._api import delete, get, head, options, patch, post, put, request, stream
from ._auth import Auth, BasicAuth, DigestAuth
from ._client import AsyncClient, Client
from ._config import Limits, PoolLimits, Proxy, Timeout, create_ssl_context
from ._exceptions import (
    CloseError,
    ConnectError,
    ConnectTimeout,
    CookieConflict,
    DecodingError,
    HTTPError,
    HTTPStatusError,
    InvalidURL,
    LocalProtocolError,
    NetworkError,
    NotRedirectResponse,
    PoolTimeout,
    ProtocolError,
    ProxyError,
    ReadError,
    ReadTimeout,
    RemoteProtocolError,
    RequestBodyUnavailable,
    RequestError,
    RequestNotRead,
    ResponseClosed,
    ResponseNotRead,
    StreamConsumed,
    StreamError,
    TimeoutException,
    TooManyRedirects,
    TransportError,
    UnsupportedProtocol,
    WriteError,
    WriteTimeout,
)
from ._models import URL, Cookies, Headers, QueryParams, Request, Response
from ._status_codes import StatusCode, codes
from ._transports.asgi import ASGITransport
from ._transports.urllib3 import URLLib3ProxyTransport, URLLib3Transport
from ._transports.wsgi import WSGITransport

__all__ = [
    "__description__",
    "__title__",
    "__version__",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "patch",
    "put",
    "request",
    "stream",
    "codes",
    "ASGITransport",
    "AsyncClient",
    "Auth",
    "BasicAuth",
    "Client",
    "DigestAuth",
    "Limits",
    "PoolLimits",
    "Proxy",
    "Timeout",
    "create_ssl_context",
    "CloseError",
    "ConnectError",
    "ConnectTimeout",
    "CookieConflict",
    "DecodingError",
    "HTTPError",
    "HTTPStatusError",
    "InvalidURL",
    "UnsupportedProtocol",
    "LocalProtocolError",
    "RemoteProtocolError",
    "NetworkError",
    "NotRedirectResponse",
    "PoolTimeout",
    "ProtocolError",
    "ReadError",
    "ReadTimeout",
    "RequestError",
    "RequestBodyUnavailable",
    "ResponseClosed",
    "ResponseNotRead",
    "RequestNotRead",
    "StatusCode",
    "StreamConsumed",
    "StreamError",
    "ProxyError",
    "TimeoutException",
    "TooManyRedirects",
    "TransportError",
    "WriteError",
    "WriteTimeout",
    "URL",
    "URLLib3Transport",
    "URLLib3ProxyTransport",
    "Cookies",
    "Headers",
    "QueryParams",
    "Request",
    "Response",
    "DigestAuth",
    "WSGITransport",
]


_locals = locals()
for name in __all__:
    if not name.startswith("__"):
        setattr(_locals[name], "__module__", "httpx")
