import sys

from .base import *
from .mock import *

if sys.platform == "emscripten":
    from .emscripten import *

    HTTPTransport = EmscriptenTransport
    AsyncHTTPTransport = AsyncEmscriptenTransport
else:
    from .asgi import *
    from .default import *
    from .wsgi import *

__all__ = [
    "ASGITransport",
    "AsyncBaseTransport",
    "BaseTransport",
    "AsyncHTTPTransport",
    "HTTPTransport",
    "MockTransport",
    "WSGITransport",
]
