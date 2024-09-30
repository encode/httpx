import sys

from .base import *
from .mock import *
from .asgi import *
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
