# Developer Interface

## Helper Functions

!!! note
    Only use these functions if you're testing HTTPX in a console
    or making a small number of requests. Using a `Client` will
    enable HTTP/2 and connection pooling for more efficient and
    long-lived connections.

* `get(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `options(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `head(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `post(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `put(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `patch(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `delete(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `request(method, url, [data], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `build_request(method, url, [data], [files], [json], [params], [headers], [cookies])`

## `Client`

*An HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc.*

```python
>>> client = httpx.Client()
>>> response = client.get('https://example.org')
```

* `def __init__([auth], [headers], [cookies], [verify], [cert], [timeout], [pool_limits], [max_redirects], [app], [dispatch])`
* `.headers` - **Headers**
* `.cookies` - **Cookies**
* `def .get(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .options(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .head(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .post(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .put(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .patch(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .delete(url, [data], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .request(method, url, [data], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .build_request(method, url, [data], [files], [json], [params], [headers], [cookies])`
* `def .send(request, [stream], [allow_redirects], [verify], [cert], [timeout])`
* `def .close()`

## `Response`

*An HTTP response.*

* `def __init__(...)`
* `.status_code` - **int**
* `.reason_phrase` - **str**
* `.http_version` - `"HTTP/2"` or `"HTTP/1.1"`
* `.url` - **URL**
* `.headers` - **Headers**
* `.content` - **bytes**
* `.text` - **str**
* `.encoding` - **str**
* `.is_redirect` - **bool**
* `.request` - **Request**
* `.cookies` - **Cookies**
* `.history` - **List[Response]**
* `.elapsed` - **timedelta**
* `def .raise_for_status()` - **None**
* `def .json()` - **Any**
* `def .read()` - **bytes**
* `def .stream()` - **bytes iterator**
* `def .raw()` - **bytes iterator**
* `def .close()` - **None**
* `def .next()` - **Response**

## `Request`

*An HTTP request. Can be constructed explicitly for more control over exactly
what gets sent over the wire.*

```python
>>> request = httpx.Request("GET", "https://example.org", headers={'host': 'example.org'})
>>> response = client.send(request)
```

* `def __init__(method, url, [params], [data], [json], [headers], [cookies])`
* `.method` - **str**
* `.url` - **URL**
* `.content` - **byte** or **byte async iterator**
* `.headers` - **Headers**
* `.cookies` - **Cookies**

## `URL`

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

## `Origin`

*A normalized, IDNA supporting set of scheme/host/port info.*

```python
>>> Origin('https://example.org') == Origin('HTTPS://EXAMPLE.ORG:443')
True
```

* `def __init__(url)`
* `.scheme` - **str**
* `.is_ssl` - **bool**
* `.host` - **str**
* `.port` - **int**

## `Headers`

*A case-insensitive multi-dict.*

```python
>>> headers = Headers({'Content-Type': 'application/json'})
>>> headers['content-type']
'application/json'
```

* `def __init__(self, headers)`

## `Cookies`

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
