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

::: httpx.RequestError

::: httpx.TransportError

::: httpx.TimeoutException

::: httpx.ConnectTimeout

::: httpx.ReadTimeout

::: httpx.WriteTimeout

::: httpx.PoolTimeout

::: httpx.NetworkError

::: httpx.ConnectError

::: httpx.ReadError

::: httpx.WriteError

::: httpx.CloseError

::: httpx.ProtocolError

::: httpx.LocalProtocolError

::: httpx.RemoteProtocolError

::: httpx.ProxyError

::: httpx.UnsupportedProtocol

::: httpx.DecodingError

::: httpx.TooManyRedirects

::: httpx.HTTPStatusError

::: httpx.InvalidURL

::: httpx.CookieConflict

::: httpx.StreamError

::: httpx.StreamConsumed

::: httpx.StreamClosed

::: httpx.ResponseNotRead

::: httpx.RequestNotRead
