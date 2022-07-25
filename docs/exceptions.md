# Exceptions

This page lists exceptions that may be raised when using HTTPX.

For an overview of how to work with HTTPX exceptions, see [Exceptions (Quickstart)](quickstart.md#exceptions).

## The exception hierarchy

* HTTPError
    * RequestError
        * TransportError
            * TimeoutException
                * ConnectTimeout
                * ReadTimeout
                * WriteTimeout
                * PoolTimeout
            * NetworkError
                * ConnectError
                * ReadError
                * WriteError
                * CloseError
            * ProtocolError
                * LocalProtocolError
                * RemoteProtocolError
            * ProxyError
            * UnsupportedProtocol
        * DecodingError
        * TooManyRedirects
    * HTTPStatusError
* InvalidURL
* CookieConflict
* StreamError
    * StreamConsumed
    * ResponseNotRead
    * RequestNotRead
    * StreamClosed

---

## Exception classes

::: httpx.HTTPError
    :docstring:

::: httpx.RequestError
    :docstring:

::: httpx.TransportError
    :docstring:

::: httpx.TimeoutException
    :docstring:

::: httpx.ConnectTimeout
    :docstring:

::: httpx.ReadTimeout
    :docstring:

::: httpx.WriteTimeout
    :docstring:

::: httpx.PoolTimeout
    :docstring:

::: httpx.NetworkError
    :docstring:

::: httpx.ConnectError
    :docstring:

::: httpx.ReadError
    :docstring:

::: httpx.WriteError
    :docstring:

::: httpx.CloseError
    :docstring:

::: httpx.ProtocolError
    :docstring:

::: httpx.LocalProtocolError
    :docstring:

::: httpx.RemoteProtocolError
    :docstring:

::: httpx.ProxyError
    :docstring:

::: httpx.UnsupportedProtocol
    :docstring:

::: httpx.DecodingError
    :docstring:

::: httpx.TooManyRedirects
    :docstring:

::: httpx.HTTPStatusError
    :docstring:

::: httpx.InvalidURL
    :docstring:

::: httpx.CookieConflict
    :docstring:

::: httpx.StreamError
    :docstring:

::: httpx.StreamConsumed
    :docstring:

::: httpx.StreamClosed
    :docstring:

::: httpx.ResponseNotRead
    :docstring:

::: httpx.RequestNotRead
    :docstring:
