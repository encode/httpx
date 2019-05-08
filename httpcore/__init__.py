from .adapters.redirects import RedirectAdapter
from .backends.sync import SyncClient
from .client import Client
from .config import PoolLimits, SSLConfig, TimeoutConfig
from .constants import Protocol, codes
from .dispatch.connection import HTTPConnection
from .dispatch.connection_pool import ConnectionPool
from .dispatch.http2 import HTTP2Connection
from .dispatch.http11 import HTTP11Connection
from .exceptions import (
    ConnectTimeout,
    DecodingError,
    InvalidURL,
    PoolTimeout,
    ProtocolError,
    ReadTimeout,
    RedirectBodyUnavailable,
    RedirectLoop,
    ResponseClosed,
    ResponseNotRead,
    StreamConsumed,
    Timeout,
    TooManyRedirects,
)
from .interfaces import Adapter, BaseReader, BaseWriter
from .models import URL, Headers, Origin, QueryParams, Request, Response

__version__ = "0.2.1"
