from .__version__ import __title__, __version__
from ._client import *  # Client
from ._content import *  # Content, File, Files, Form, HTML, JSON, MultiPart, Text
from ._headers import *  # Headers
from ._network import *  # NetworkBackend, NetworkStream, timeout
from ._parsers import *  # HTTPParser, ProtocolError
from ._pool import *  # Connection, ConnectionPool, Transport
from ._quickstart import *  # get, post, put, patch, delete
from ._response import *  # Response
from ._request import *  # Request
from ._streams import *  # ByteStream, DuplexStream, FileStream, HTTPStream, Stream
from ._server import *  # serve_http, run
from ._urlencode import *  # quote, unquote, urldecode, urlencode
from ._urls import *  # QueryParams, URL


__all__ = [
    "__title__",
    "__version__",
    "ByteStream",
    "Client",
    "Connection",
    "ConnectionPool",
    "Content",
    "delete",
    "DuplexStream",
    "File",
    "FileStream",
    "Files",
    "Form",
    "get",
    "Headers",
    "HTML",
    "HTTPParser",
    "HTTPStream",
    "JSON",
    "MultiPart",
    "NetworkBackend",
    "NetworkStream",
    "open_connection",
    "post",
    "ProtocolError",
    "put",
    "patch",
    "Response",
    "Request",
    "run",
    "serve_http",
    "Stream",
    "Text",
    "timeout",
    "Transport",
    "QueryParams",
    "quote",
    "unquote",
    "URL",
    "urldecode",
    "urlencode",
]


__locals = locals()
for __name in __all__:
    if not __name.startswith('__'):
        setattr(__locals[__name], "__module__", "httpx")
