"""
Dispatch classes handle the raw network connections and the implementation
details of making the HTTP request and receiving the response.
"""
from .asgi import ASGIDispatch
from .wsgi import WSGIDispatch

__all__ = ["ASGIDispatch", "WSGIDispatch"]
