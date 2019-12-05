# QuickStart

!!! note
    The standard Python REPL does not allow top-level async statements.

    To run async examples directly you'll probably want to either use `ipython`,
    or use Python 3.8 with `python -m asyncio`.

First, start by importing HTTPX:

```python
>>> import httpx
```

Now, let’s try to get a webpage.

```python
>>> r = await httpx.get('https://httpbin.org/get')
>>> r
<Response [200 OK]>
```

Similarly, to make an HTTP POST request:

```python
>>> r = await httpx.post('https://httpbin.org/post', data={'key': 'value'})
```

The PUT, DELETE, HEAD, and OPTIONS requests all follow the same style:

```python
>>> r = await httpx.put('https://httpbin.org/put', data={'key': 'value'})
>>> r = await httpx.delete('https://httpbin.org/delete')
>>> r = await httpx.head('https://httpbin.org/get')
>>> r = await httpx.options('https://httpbin.org/get')
```

## Passing Parameters in URLs

To include URL query parameters in the request, use the `params` keyword:

```python
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> r = await httpx.get('https://httpbin.org/get', params=params)
```

To see how the values get encoding into the URL string, we can inspect the
resulting URL that was used to make the request:

```python
>>> r.url
URL('https://httpbin.org/get?key2=value2&key1=value1')
```

You can also pass a list of items as a value:

```python
>>> params = {'key1': 'value1', 'key2': ['value2', 'value3']}
>>> r = await httpx.get('https://httpbin.org/get', params=params)
>>> r.url
URL('https://httpbin.org/get?key1=value1&key2=value2&key2=value3')
```

## Response Content

HTTPX will automatically handle decoding the response content into Unicode text.

```python
>>> r = await httpx.get('https://www.example.org/')
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

You can inspect what encoding has been used to decode the response.

```python
>>> r.encoding
'UTF-8'
```

If you need to override the standard behavior and explicitly set the encoding to
use, then you can do that too.

```python
>>> r.encoding = 'ISO-8859-1'
```

## Binary Response Content

The response content can also be accessed as bytes, for non-text responses:

```python
>>> r.content
b'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

Any `gzip` and `deflate` HTTP response encodings will automatically
be decoded for you. If `brotlipy` is installed, then the `brotli` response
encoding will also be supported.

For example, to create an image from binary data returned by a request, you can use the following code:

```python
>>> from PIL import Image
>>> from io import BytesIO
>>> i = Image.open(BytesIO(r.content))
```

## JSON Response Content

Often Web API responses will be encoded as JSON.

```python
>>> r = await httpx.get('https://api.github.com/events')
>>> r.json()
[{u'repository': {u'open_issues': 0, u'url': 'https://github.com/...' ...  }}]
```

## Custom Headers

To include additional headers in the outgoing request, use the `headers` keyword argument:

```python
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> r = await httpx.get(url, headers=headers)
```

## Sending Form Encoded Data

Some types of HTTP requests, such as `POST` and `PUT` requests, can include data
in the request body. One common way of including that is as form-encoded data,
which is used for HTML forms.

```python
>>> data = {'key1': 'value1', 'key2': 'value2'}
>>> r = await httpx.post("https://httpbin.org/post", data=data)
>>> print(r.text)
{
  ...
  "form": {
    "key2": "value2",
    "key1": "value1"
  },
  ...
}
```

Form encoded data can also include multiple values form a given key.

```python
>>> data = {'key1': ['value1', 'value2']}
>>> r = await httpx.post("https://httpbin.org/post", data=data)
>>> print(r.text)
{
  ...
  "form": {
    "key1": [
      "value1",
      "value2"
    ]
  },
  ...
}
```

## Sending Multipart File Uploads

You can also upload files, using HTTP multipart encoding:

```python
>>> files = {'upload-file': open('report.xls', 'rb')}
>>> r = await httpx.post("https://httpbin.org/post", files=files)
>>> print(r.text)
{
  ...
  "files": {
    "upload-file": "<... binary content ...>"
  },
  ...
}
```

You can also explicitly set the filename and content type, by using a tuple
of items for the file value:

```python
>>> files = {'upload-file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel')}
>>> r = await httpx.post("https://httpbin.org/post", files=files)
>>> print(r.text)
{
  ...
  "files": {
    "upload-file": "<... binary content ...>"
  },
  ...
}
```

## Sending JSON Encoded Data

Form encoded data is okay if all you need is a simple key-value data structure.
For more complicated data structures you'll often want to use JSON encoding instead.

```python
>>> data = {'integer': 123, 'boolean': True, 'list': ['a', 'b', 'c']}
>>> r = await httpx.post("https://httpbin.org/post", json=data)
>>> print(r.text)
{
  ...
  "json": {
    "boolean": true,
    "integer": 123,
    "list": [
      "a",
      "b",
      "c"
    ]
  },
  ...
}
```

## Sending Binary Request Data

For other encodings, you should use either a `bytes` type or a generator
that yields `bytes`.

You'll probably also want to set a custom `Content-Type` header when uploading
binary data.

## Response Status Codes

We can inspect the HTTP status code of the response:

```python
>>> r = await httpx.get('https://httpbin.org/get')
>>> r.status_code
200
```

HTTPX also includes an easy shortcut for accessing status codes by their text phrase.

```python
>>> r.status_code == httpx.codes.OK
True
```

We can raise an exception for any Client or Server error responses (4xx or 5xx status codes):

```python
>>> not_found = await httpx.get('https://httpbin.org/status/404')
>>> not_found.status_code
404
>>> not_found.raise_for_status()
Traceback (most recent call last):
  File "/Users/tomchristie/GitHub/encode/httpcore/httpx/models.py", line 776, in raise_for_status
    raise HttpError(message)
httpx.exceptions.HttpError: 404 Not Found
```

Any successful response codes will simply return `None` rather than raising an exception.

``` python
>>> r.raise_for_status()
```

## Response Headers

The response headers are available as a dictionary-like interface.

```python
>>> r.headers
Headers({
    'content-encoding': 'gzip',
    'transfer-encoding': 'chunked',
    'connection': 'close',
    'server': 'nginx/1.0.4',
    'x-runtime': '148ms',
    'etag': '"e1ca502697e5c9317743dc078f67693f"',
    'content-type': 'application/json'
})
```

The `Headers` data type is case-insensitive, so you can use any capitalization.

```python
>>> r.headers['Content-Type']
'application/json'

>>> r.headers.get('content-type')
'application/json'
```

Multiple values for a single response header are represented as a single comma-separated
value, as per [RFC 7230](https://tools.ietf.org/html/rfc7230#section-3.2):

> A recipient MAY combine multiple header fields with the same field name into one “field-name: field-value” pair, without changing the semantics of the message, by appending each subsequent field-value to the combined field value in order, separated by a comma.

## Cookies

Any cookies that are set on the response can be easily accessed:

```python
>>> r = await httpx.get('http://httpbin.org/cookies/set?chocolate=chip', allow_redirects=False)
>>> r.cookies['chocolate']
'chip'
```

To include cookies in an outgoing request, use the `cookies` parameter:

```python
>>> cookies = {"peanut": "butter"}
>>> r = await httpx.get('http://httpbin.org/cookies', cookies=cookies)
>>> r.json()
{'cookies': {'peanut': 'butter'}}
```

Cookies are returned in a `Cookies` instance, which is a dict-like data structure
with additional API for accessing cookies by their domain or path.

```python
>>> cookies = httpx.Cookies()
>>> cookies.set('cookie_on_domain', 'hello, there!', domain='httpbin.org')
>>> cookies.set('cookie_off_domain', 'nope.', domain='example.org')
>>> r = await httpx.get('http://httpbin.org/cookies', cookies=cookies)
>>> r.json()
{'cookies': {'cookie_on_domain': 'hello, there!'}}
```

## Redirection and History

By default, HTTPX will follow redirects for anything except `HEAD` requests.

The `history` property of the response can be used to inspect any followed redirects.
It contains a list of all any redirect responses that were followed, in the order
in which they were made.

For example, GitHub redirects all HTTP requests to HTTPS.

```python
>>> r = await httpx.get('http://github.com/')
>>> r.url
URL('https://github.com/')
>>> r.status_code
200
>>> r.history
[<Response [301 Moved Permanently]>]
```

You can modify the default redirection handling with the allow_redirects parameter:

```python
>>> r = await httpx.get('http://github.com/', allow_redirects=False)
>>> r.status_code
301
>>> r.history
[]
```

If you’re making a `HEAD` request, you can use this to enable redirection:

```python
>>> r = await httpx.head('http://github.com/', allow_redirects=True)
>>> r.url
'https://github.com/'
>>> r.history
[<Response [301 Moved Permanently]>]
```

## Timeouts

HTTPX defaults to including reasonable timeouts for all network operations,
meaning that if a connection is not properly established then it should always
raise an error rather than hanging indefinitely.

The default timeout for network inactivity is five seconds. You can modify the
value to be more or less strict:

```python
>>> await httpx.get('https://github.com/', timeout=0.001)
```

You can also disable the timeout behaviour completely...

```python
>>> await httpx.get('https://github.com/', timeout=None)
```

For advanced timeout management, see [Timeout fine-tuning](https://www.encode.io/httpx/advanced/#timeout-fine-tuning).

## Authentication

HTTPX supports Basic and Digest HTTP authentication.

To provide Basic authentication credentials, pass a 2-tuple of
plaintext `str` or `bytes` objects as the `auth` argument to the request
functions:

```python
>>> await httpx.get("https://example.com", auth=("my_user", "password123"))
```

To provide credentials for Digest authentication you'll need to instantiate
a `DigestAuth` object with the plaintext username and password as arguments.
This object can be then passed as the `auth` argument to the request methods
as above:

```python
>>> auth = httpx.DigestAuth("my_user", "password123")
>>> await httpx.get("https://example.com", auth=auth)
<Response [200 OK]>
```
