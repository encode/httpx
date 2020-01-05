"""
Dispatch classes handle the raw network connections and the implementation
details of making the HTTP request and receiving the response.
"""
from .._async.dispatch.app import AsyncAppDispatch as ASGIDispatch

__all__ = ["ASGIDispatch"]
