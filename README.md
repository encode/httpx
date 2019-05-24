# HTTPCore

<a href="https://travis-ci.org/encode/httpcore">
    <img src="https://travis-ci.org/encode/httpcore.svg?branch=master" alt="Build Status">
</a>
<a href="https://codecov.io/gh/encode/httpcore">
    <img src="https://codecov.io/gh/encode/httpcore/branch/master/graph/badge.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/httpcore/">
    <img src="https://badge.fury.io/py/httpcore.svg" alt="Package version">
</a>

## Feature support

* `HTTP/2` and `HTTP/1.1` support.
* `async`/`await` support for non-blocking HTTP requests.
* Strict timeouts everywhere by default.
* Fully type annotated.
* 100% test coverage.

Plus all the standard features of requests...

* International Domains and URLs
* Keep-Alive & Connection Pooling
* Sessions with Cookie Persistence
* Browser-style SSL Verification
* Basic/Digest Authentication *TODO - We have Basic, but not Digest yet.*
* Elegant Key/Value Cookies
* Automatic Decompression
* Automatic Content Decoding
* Unicode Response Bodies
* Multipart File Uploads *TODO - Request content currently supports URL encoded data, JSON, bytes, or async byte iterators.*
* HTTP(S) Proxy Support *TODO*
* Connection Timeouts
* Streaming Downloads
* .netrc Support *TODO*
* Chunked Requests

## Usage

Making a request:

```python
>>> import httpcore
>>> client = httpcore.Client()
>>> response = client.get('https://example.com')
>>> response.status_code
<HTTPStatus.OK: 200>
>>> response.protocol
'HTTP/2'
>>> response.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>\n...'
```

Alternatively, async requests:

**Note**: Use `ipython` to try this from the console, since it supports `await`.

```python
>>> import httpcore
>>> client = httpcore.AsyncClient()
>>> response = await client.get('https://example.com')
>>> response.status_code
<StatusCode.OK: 200>
>>> response.protocol
'HTTP/2'
>>> response.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>\n...'
```

---

## Dependencies

* `h2` - HTTP/2 support.
* `h11` - HTTP/1.1 support.
* `certifi` - SSL certificates.
* `chardet` - Fallback auto-detection for response encoding.
* `idna` - Internationalized domain name support.
* `rfc3986` - URL parsing & normalization.
* `brotlipy` - Decoding for "brotli" compressed responses. *(Optional)*

A huge amount of credit is due to `requests` for the API layout that
much of this work follows, as well as to `urllib3` for plenty of design
inspiration around the lower level networking details.

---

## API Reference

### `Client`

*An HTTP client, with connection pooling, redirects, cookie persistence, etc.*

```python
>>> client = Client()
>>> response = client.get('https://example.org')
```

* `def __init__([auth], [cookies], [verify], [cert], [timeout], [pool_limits], [max_redirects], [dispatch])`
* `def .request(method, url, [data], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .get(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .options(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .head(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .post(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .put(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .patch(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .delete(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .prepare_request(request)`
* `def .send(request, [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .close()`

### `Response`

*An HTTP response.*

* `def __init__(...)`
* `.status_code` - **int** *(Typically a `StatusCode` IntEnum.)*
* `.reason_phrase` - **str**
* `.protocol` - `"HTTP/2"` or `"HTTP/1.1"`
* `.url` - **URL**
* `.headers` - **Headers**
* `.content` - **bytes**
* `.text` - **str**
* `.encoding` - **str**
* `.is_redirect` - **bool**
* `.request` - **Request**
* `.cookies` - **Cookies**
* `.history` - **List[Response]**
* `def .raise_for_status()` - **None**
* `def .json()` - **Any**
* `def .read()` - **bytes**
* `def .stream()` - **bytes iterator**
* `def .raw()` - **bytes iterator**
* `def .close()` - **None**
* `def .next()` - **Response**

### `Request`

*An HTTP request. Can be constructed explicitly for more control over exactly
what gets sent over the wire.*

```python
>>> request = Request("GET", "https://example.org", headers={'host': 'example.org'})
>>> response = client.send(request)
```

* `def __init__(method, url, [params], [data], [json], [headers], [cookies])`
* `.method` - **str**
* `.url` - **URL**
* `.content` - **byte** or **byte async iterator**
* `.headers` - **Headers**
* `.cookies` - **Cookies**

### `URL`

*A normalized, IDNA supporting URL.*

```python
>>> url = URL("https://example.org/")
>>> url.host
'example.org'
```

* `def __init__(url, allow_relative=False, params=None)`
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

* `def __init__(self, headers)`

### `Cookies`

*A dict-like cookie store.*

```python
>>> cookies = Cookies()
>>> cookies.set("name", "value", domain="example.org")
```

* `def __init__(cookies: [dict, Cookies, CookieJar])`
* `.jar` - **CookieJar**
* `def extract_cookies(response)`
* `def set_cookie_header(request)`
* `def set(name, value, [domain], [path])`
* `def get(name, [domain], [path])`
* `def delete(name, [domain], [path])`
* `def clear([domain], [path])`
* *Standard mutable mapping interface*

___

## Alternate backends

### `AsyncClient`

An asyncio client.

### `TrioClient`

*TODO*

---

## The Stack

There are two main layers in the stack. The client handles redirection,
cookie persistence (TODO), and authentication (TODO). The dispatcher
handles sending the actual request and getting the response.

* `Client` - Redirect, authentication, cookies etc.
* `ConnectionPool(Dispatcher)` - Connection pooling & keep alive.
  * `HTTPConnection` - A single connection.
    * `HTTP11Connection` - A single HTTP/1.1 connection.
    * `HTTP2Connection` - A single HTTP/2 connection, with multiple streams.
