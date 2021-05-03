# Requests Compatibility Guide

HTTPX aims to be broadly compatible with the `requests` API.

This documentation outlines places where the API differs...

## Request URLs

Accessing `response.url` will return a `URL` instance, rather than a string.
Use `str(response.url)` if you need a string instance.

## Request Content

For uploading raw text or binary content we prefer to use a `content` parameter,
in order to better separate this usage from the case of uploading form data.

For example, using `content=...` to upload raw content:

```python
# Uploading text, bytes, or a bytes iterator.
httpx.post(..., content=b"Hello, world")
```

And using `data=...` to send form data:

```python
# Uploading form data.
httpx.post(..., data={"message": "Hello, world"})
```

Using the `data=<text/byte content>` will raise a deprecation warning,
and is expected to be fully removed with the HTTPX 1.0 release.

## Content encoding

HTTPX uses `utf-8` for encoding `str` request bodies. For example, when using `content=<str>` the request body will be encoded to `utf-8` before being sent over the wire. This differs from Requests which uses `latin1`. If you need an explicit encoding, pass encoded bytes explictly, e.g. `content=<str>.encode("latin1")`.

For response bodies, assuming the server didn't send an explicit encoding then HTTPX will do its best to figure out an appropriate encoding. Unlike Requests which uses the `chardet` library, HTTPX relies on a plainer fallback strategy (basically attempting UTF-8, or using Windows-1252 as a fallback). This strategy should be robust enough to handle the vast majority of use cases.

## Cookies

If using a client instance, then cookies should always be set on the client rather than on a per-request basis.

This usage is supported:

```python
client = httpx.Client(cookies=...)
client.post(...)
```

This usage is **not** supported:

```python
client = httpx.Client()
client.post(..., cookies=...)
```

We prefer enforcing a stricter API here because it provides clearer expectations around cookie persistence, particularly when redirects occur.

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

## Proxy keys

When using `httpx.Client(proxies={...})` to map to a selection of different proxies, we use full URL schemes, such as `proxies={"http://": ..., "https://": ...}`.

This is different to the `requests` usage of `proxies={"http": ..., "https": ...}`.

This change is for better consistency with more complex mappings, that might also include domain names, such as `proxies={"all://": ..., "all://www.example.com": None}` which maps all requests onto a proxy, except for requests to "www.example.com" which have an explicit exclusion.

Also note that `requests.Session.request(...)` allows a `proxies=...` parameter, whereas `httpx.Client.request(...)` does not.

## SSL configuration

When using a `Client` instance, the `trust_env`, `verify`, and `cert` arguments should always be passed on client instantiation, rather than passed to the request method.

If you need more than one different SSL configuration, you should use different client instances for each SSL configuration.

Requests supports `REQUESTS_CA_BUNDLE` which points to either a file or a directory. HTTPX supports the `SSL_CERT_FILE` (for a file) and `SSL_CERT_DIR` (for a directory) OpenSSL variables instead.

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

There is no notion of [prepared requests](https://requests.readthedocs.io/en/stable/user/advanced/#prepared-requests) in HTTPX. If you need to customize request instantiation, see [Request instances](advanced.md#request-instances).

Besides, `httpx.Request()` does not support the `auth`, `timeout`, `allow_redirects`, `proxies`, `verify` and `cert` parameters. However these are available in `httpx.request`, `httpx.get`, `httpx.post` etc., as well as on [`Client` instances](advanced.md#client-instances).

## Mocking

If you need to mock HTTPX the same way that test utilities like `responses` and `requests-mock` does for `requests`, see [RESPX](https://github.com/lundberg/respx).

## Networking layer

`requests` defers most of its HTTP networking code to the excellent [`urllib3` library](https://urllib3.readthedocs.io/en/latest/).

On the other hand, HTTPX uses [HTTPCore](https://github.com/encode/httpcore) as its core HTTP networking layer, which is a different project than `urllib3`.

## Query Parameters

`requests` omits `params` whose values are `None` (e.g. `requests.get(..., params={"foo": None})`). This is not supported by HTTPX.

## HEAD redirection

In `requests`, all top-level API follow redirects by default except `HEAD`.
In consideration of consistency, we make `HEAD` follow redirects by default in HTTPX.

## Determining the next redirect request

When using `allow_redirects=False`, the `requests` library exposes an attribute `response.next`, which can be used to obtain the next redirect request.

In HTTPX, this attribute is instead named `response.next_request`. For example:

```python
client = httpx.Client()
request = client.build_request("GET", ...)
while request is not None:
    response = client.send(request, allow_redirects=False)
    request = response.next_request
```

## Event Hooks

`requests` allows event hooks to mutate `Request` and `Response` objects. See [examples](https://requests.readthedocs.io/en/master/user/advanced/#event-hooks) given in the documentation for `requests`.

In HTTPX, event hooks may access properties of requests and responses, but event hook callbacks cannot mutate the original request/response.

If you are looking for more control, consider checking out [Custom Transports](advanced.md#custom-transports).
