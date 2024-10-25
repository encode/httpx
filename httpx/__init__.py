from .__version__ import __description__, __title__, __version__
from ._api import *
from ._auth import *
from ._client import *
from ._config import *
from ._content import *
from ._exceptions import *
from ._models import *
from ._status_codes import *
from ._transports import *
from ._types import *
from ._urls import *

try:
    from ._main import main
except ImportError:  # pragma: no cover

    def main() -> None:  # type: ignore
        import sys

        print(
            "The httpx command line client could not run because the required "
            "dependencies were not installed.\nMake sure you've installed "
            "everything with: pip install 'httpx[cli]'"
        )
        sys.exit(1)


__all__ = [
    # Packaging.      `__version__.py`
    "__description__",
    "__title__",
    "__version__",
    # Top level API.  `_api.py`
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "request",
    "stream",
    # Authentication. `_auth.py`
    "Auth",
    "BasicAuth",
    "DigestAuth",
    "NetRCAuth",
    # Client.         `_client.py`
    "AsyncClient",
    "Client",
    "USE_CLIENT_DEFAULT",
    # Config.         `_config.py`
    "create_ssl_context",
    "Limits",
    "Proxy",
    "Timeout",
    # Content.        `_content.py`
    "ByteStream",
    # Exceptions.     `_exceptions.py`
    "CloseError",
    "ConnectError",
    "ConnectTimeout",
    "CookieConflict",
    "DecodingError",
    "HTTPError",
    "HTTPStatusError",
    "InvalidURL",
    "LocalProtocolError",
    "NetworkError",
    "PoolTimeout",
    "ProtocolError",
    "ProxyError",
    "ReadError",
    "ReadTimeout",
    "RemoteProtocolError",
    "RequestError",
    "RequestNotRead",
    "ResponseNotRead",
    "StreamClosed",
    "StreamConsumed",
    "StreamError",
    "TimeoutException",
    "TooManyRedirects",
    "TransportError",
    "UnsupportedProtocol",
    "WriteError",
    "WriteTimeout",
    # Models.         `_models.py`
    "Cookies",
    "Headers",
    "Request",
    "Response",
    # Status Codes.   `_status_codes.py`
    "codes",
    # Transports.     `_transports/*.py`
    "ASGITransport",
    "AsyncBaseTransport",
    "AsyncHTTPTransport",
    "BaseTransport",
    "HTTPTransport",
    "MockTransport",
    "WSGITransport",
    # Types.          `_types.py`
    "AsyncByteStream",
    "SyncByteStream",
    # URLs.           `_urls.py`
    "QueryParams",
    "URL",
    # CLI             `_main.py`
    "main",
]


__locals = locals()
for __name in __all__:
    if not __name.startswith("__"):
        setattr(__locals[__name], "__module__", "httpx")  # noqa
