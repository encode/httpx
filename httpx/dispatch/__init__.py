"""
Dispatch classes handle the raw network connections and the implementation
details of making the HTTP request and receiving the response.
"""
from .asgi import ASGIDispatch

__all__ = ["ASGIDispatch"]
