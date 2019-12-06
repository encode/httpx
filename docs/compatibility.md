# Requests Compatibility Guide

HTTPX aims to be compatible with the `requests` API wherever possible.

This documentation outlines places where the API differs...

## QuickStart

Pretty much any API mentioned in the `requests` QuickStart should be identical
to the API in our own documentation. The following exceptions apply:

* `Response.url` - Returns a `URL` instance, rather than a string. Use `str(response.url)` if you need a string instance.
* `httpx.codes` - In our documentation we prefer the uppercased versions, such as `codes.NOT_FOUND`, but also provide lower-cased versions for API compatibility with `requests`.
* `stream()`. - HTTPX provides a `.stream()` interface rather than using `stream=True`. This ensures that streaming responses are always properly closed outside of the stream block, and makes it visually clearer at which points streaming I/O APIs may be used with a response. Streaming request data is made avialable with `.stream_bytes()`, `.stream_text()`, `.stream_lines()`, and `.stream_raw()`.
* `.get`, `.delete`, `.head`, `.options` -  These methods do not support `files`, `data`, or `json` arguments. Use `.request` if you need to need to send data using these http methods.
* We don't support `response.is_ok` since the naming is ambiguous there, and might incorrectly imply an equivalence to `response.status_code == codes.OK`. Instead we provide the `response.is_error` property. Use `if not response.is_error:` instead of `if response.is_ok:`.

## Advanced Usage

### requests.Session

The HTTPX equivalent of `requests.Session` is `httpx.Client`.

```python
session = requests.Session(**kwargs)
```

is generally equivalent to

```python
client = httpx.Client(**kwargs)
```

More detailed documentation and usage of `Client` can be found in [Advanced Usage](advanced.md).

## Mocking

If you need to mock HTTPX the same way that test utilities like `responses` and `requests-mock` does for `requests`, see [RESPX](https://github.com/lundberg/respx).
