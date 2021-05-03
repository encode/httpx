# Exceptions

## Request and Response exceptions

The most important exception classes in HTTPX are `RequestError` and `HTTPStatusError`.

The `RequestError` class is a superclass that encompasses any exception that occurs
while issuing an HTTP request. These exceptions include a `.request` attribute.

```python
try:
    response = httpx.get("https://www.example.com/")
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}.")
```

The `HTTPStatusError` class is raised by `response.raise_for_status()` on 4xx and 5xx responses.
These exceptions include both a `.request` and a `.response` attribute.

```python
response = httpx.get("https://www.example.com/")
try:
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
```

There is also a base class `HTTPError` that includes both of these categories, and can be used
to catch either failed requests, or 4xx and 5xx responses.

You can either use this base class to catch both categories...

```python
try:
    response = httpx.get("https://www.example.com/")
    response.raise_for_status()
except httpx.HTTPError as exc:
    print(f"Error while requesting {exc.request.url!r}.")
```

Or handle each case explicitly...

```python
try:
    response = httpx.get("https://www.example.com/")
    response.raise_for_status()
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}.")
except httpx.HTTPStatusError as exc:
    print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
```

---

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
    * ResponseClosed

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
