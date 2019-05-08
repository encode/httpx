# HTTPCore

A proposal for [requests III](https://github.com/kennethreitz/requests3).

## Feature support

* `HTTP/1.1` and `HTTP/2` Support.
* `async`/`await` support for non-thread-blocking HTTP requests.
* Fully type annotated.
* 100% test coverage. *TODO - We're on ~97% right now*

Plus all the standard features of requests...

* International Domains and URLs
* Keep-Alive & Connection Pooling
* Sessions with Cookie Persistence *TODO - Requires `adapters/cookies.py` implementation.*
* Browser-style SSL Verification
* Basic/Digest Authentication *TODO - Requires `adapters/authentication.py` implementation.*
* Elegant Key/Value Cookies *TODO*
* Automatic Decompression
* Automatic Content Decoding
* Unicode Response Bodies
* Multipart File Uploads *TODO - Request content currently supports bytes or async byte iterators.*
* HTTP(S) Proxy Support *TODO*
* Connection Timeouts
* Streaming Downloads
* .netrc Support *TODO - Requires `adapters/environment.py` implementation.*
* Chunked Requests

## Usage

**Note**: Use `ipython` to try this from the console, since it supports `await`.

Making a request:

```python
>>> import httpcore
>>> client = httpcore.Client()
>>> response = await client.get('https://example.com')
>>> response.status_code
<StatusCode.ok: 200>
>>> response.protocol
'HTTP/2'
>>> response.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>\n...'
```

Alternatively, thread-synchronous requests:

```python
>>> import httpcore
>>> client = httpcore.SyncClient()
>>> response = client.get('https://example.com')
>>> response.status_code
<StatusCode.ok: 200>
>>> response.protocol
'HTTP/2'
>>> response.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>\n...'
```

---

## Dependencies

* `h11` - HTTP/1.1 support.
* `h2` - HTTP/2 support.
* `certifi` - SSL certificates.
* `chardet` - Fallback auto-detection for response encoding.
* `idna` - Internationalized domain name support.
* `rfc3986` - URL parsing & normalization.
* `brotlipy` - Decoding for "brotli" compressed responses. *(Optional)*

Additionally, credit is due to for `urllib3` for plenty of design inspiration.

---

## API Reference

### `Client`

*An HTTP client, with connection pooling, redirects, cookie persistence, etc.*

```python
>>> client = Client()
>>> response = await client.get('https://example.org')
```

* `def __init__([ssl], [timeout], [pool_limits], [max_redirects])`
* `async def .request(method, url, [content], [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .get(url, [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .options(url, [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .head(url, [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .post(url, [content], [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .put(url, [content], [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .patch(url, [content], [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `async def .delete(url, [content], [query_params], [headers], [stream], [allow_redirects], [ssl], [timeout])`
* `def .prepare_request(request)`
* `async def .send(request, [stream], [allow_redirects], [ssl], [timeout])`
* `async def .close()`

### `Response`

*An HTTP response.*

* `def __init__(...)`
* `.status_code` - **int**
* `.reason_phrase` - **str**
* `.protocol` - `"HTTP/2"` or `"HTTP/1.1"`
* `.url` - **URL**
* `.headers` - **Headers**
* `.content` - **bytes**
* `.text` - **str**
* `.encoding` - **str**
* `.is_redirect` - **bool**
* `.request` - **Request**
* `.cookies` - **Cookies** *TODO*
* `.history` - **List[Response]**
* `def .raise_for_status()` - **None**
* `def .json()` - **Any** *TODO*
* `async def .read()` - **bytes**
* `async def .stream()` - **bytes iterator**
* `async def .raw()` - **bytes iterator**
* `async def .close()` - **None**
* `async def .next()` - **Response**

### `Request`

*An HTTP request. Can be constructed explicitly for more control over exactly
what gets sent over the wire.*

```python
>>> request = Request("GET", "https://example.org", headers={'host': 'example.org'})
>>> response = await client.send(request)
```

* `def __init__(method, url, query_params, content, headers)`
* `.method` - **str** (Uppercased)
* `.url` - **URL**
* `.content` - **byte** or **byte async iterator**
* `.headers` - **Headers**

### `URL`

*A normalized, IDNA supporting URL.*

```python
>>> url = URL("https://example.org/")
>>> url.host
'example.org'
```

* `def __init__(url, allow_relative=False, query_params=None)`
* `.scheme` - **str**
* `.authority` - **str**
* `.host` - **str**
* `.port` - **int**
* `.path` - **str**
* `.query` - **str**
* `.full_path` - **str**
* `.fragment` - **str**
* `.is_ssl` - **bool**
* `.origin` - **Origin**
* `.is_absolute_url` - **bool**
* `.is_relative_url` - **bool**
* `def .copy_with([scheme], [authority], [path], [query], [fragment])` - **URL**
* `def .resolve_with(url)` - **URL**

### `Origin`

*A normalized, IDNA supporting set of scheme/host/port info.*

```python
>>> Origin('https://example.org') == Origin('HTTPS://EXAMPLE.ORG:443')
True
```

* `def __init__(url)`
* `.is_ssl` - **bool**
* `.host` - **str**
* `.port` - **int**

### `Headers`

*A case-insensitive multi-dict.*

```python
>>> headers = Headers({'Content-Type': 'application/json'})
>>> headers['content-type']
'application/json'
```

* `def __init__(headers)`

___

## Alternate backends

### `SyncClient`

A thread-synchronous client.

### `TrioClient`

*TODO*

---

## The Stack

The `httpcore` client builds up behavior in a modular way.

This makes it easier to dig into an understand the behaviour of any one aspect in isolation, as well as making it easier to test or to adapt for custom behaviors.

You can also use lower level components in isolation if required, eg. Use a `ConnectionPool` without providing sessions, redirects etc...

* `RedirectAdapter` - Adds redirect support.
* `EnvironmentAdapter` - Adds `.netrc` and envvars such as `REQUESTS_CA_BUNDLE`.
* `CookieAdapter` - Adds cookie persistence.
* `AuthAdapter` - Adds authentication support.
* `ConnectionPool` - Connection pooling & keep alive.
  * `HTTPConnection` - A single connection.
    * `HTTP11Connection` - A single HTTP/1.1 connection.
    * `HTTP2Connection` - A single HTTP/2 connection, with multiple streams.
