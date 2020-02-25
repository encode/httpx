# Requests Compatibility Guide

HTTPX aims to be compatible with the `requests` API wherever possible.

This documentation outlines places where the API differs...

## Request URLs

Accessing `response.url` will return a `URL` instance, rather than a string.
Use `str(response.url)` if you need a string instance.

## Status Codes

In our documentation we prefer the uppercased versions, such as `codes.NOT_FOUND`, but also provide lower-cased versions for API compatibility with `requests`.

Requests includes various synonyms for status codes that HTTPX does not support.

## Streaming responses

HTTPX provides a `.stream()` interface rather than using `stream=True`. This ensures that streaming responses are always properly closed outside of the stream block, and makes it visually clearer at which points streaming I/O APIs may be used with a response.

For example:

```python
with request.stream("GET", "https://www.example.com") as response:
    ...
```

Within a `stream()` block request data is made available with:

* `.iter_bytes()` - Instead of `response.iter_content()`
* `.iter_text()` - Instead of `response.iter_content(decode_unicode=True)`
* `.iter_lines()` - Corresponding to `response.iter_lines()`
* `.iter_raw()` - Use this instead of `response.raw`
* `.read()` - Read the entire response body, making `request.text` and `response.content` available.

## SSL configuration

When using a `Client` instance, the `trust_env`, `verify`, and `cert` arguments should always be passed on client instantiation, rather than passed to the request method.

If you need more than one different SSL configuration, you should use different client instances for each SSL configuration.

## Request body on HTTP methods

The HTTP `GET`, `DELETE`, `HEAD`, and `OPTIONS` methods are specified as not supporting a request body. To stay in line with this, the `.get`, `.delete`, `.head` and `.options` functions do not support `files`, `data`, or `json` arguments.

If you really do need to send request data using these http methods you should use the generic `.request` function instead.

## Checking for 4xx/5xx responses

We don't support `response.is_ok` since the naming is ambiguous there, and might incorrectly imply an equivalence to `response.status_code == codes.OK`. Instead we provide the `response.is_error` property. Use `if not response.is_error:` instead of `if response.is_ok:`.

## Client instances

The HTTPX equivalent of `requests.Session` is `httpx.Client`.

```python
session = requests.Session(**kwargs)
```

is generally equivalent to

```python
client = httpx.Client(**kwargs)
```

## Request instantiation

Whenever you get a `Response` from an API call, the `request` attribute is actually the `Request` that was used internally. There are cases in which you want to build a `Request` object but don't want to send it immediately. Here is how you can do it.

```python
req = httpx.Request("GET", "https://example.org")
```

The above request object is ready to be sent. There’s no need for `prepare_request()` in HTTPX.

```python
with httpx.Client() as client:
    r = client.send(req)
```

If you need to build a request while applying client defaults, see [here](https://www.python-httpx.org/advanced/#build-request).

The list of arguments that are not present in `httpx.Request` class are `auth`, `timeout`, `allow_redirects`, `proxies`, `verify` and `cert` however these are available in `httpx.request`, `httpx.get`, `httpx.post` etc.

## Mocking

If you need to mock HTTPX the same way that test utilities like `responses` and `requests-mock` does for `requests`, see [RESPX](https://github.com/lundberg/respx).
