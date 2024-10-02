import sys

from .asgi import *
from .base import *
from .mock import *
from .wsgi import *

if sys.platform == "emscripten":
    from .emscripten import *

    HTTPTransport = EmscriptenTransport
    AsyncHTTPTransport = AsyncEmscriptenTransport

else:
    from .default import *

__all__ = [
    "ASGITransport",
    "AsyncBaseTransport",
    "BaseTransport",
    "AsyncHTTPTransport",
    "HTTPTransport",
    "MockTransport",
    "WSGITransport",
]
