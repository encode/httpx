# QuickStart

First, start by importing HTTPX:

```pycon
>>> import httpx
```

Now, let’s try to get a webpage.

```pycon
>>> r = httpx.get('https://httpbin.org/get')
>>> r
<Response [200 OK]>
```

Similarly, to make an HTTP POST request:

```pycon
>>> r = httpx.post('https://httpbin.org/post', data={'key': 'value'})
```

The PUT, DELETE, HEAD, and OPTIONS requests all follow the same style:

```pycon
>>> r = httpx.put('https://httpbin.org/put', data={'key': 'value'})
>>> r = httpx.delete('https://httpbin.org/delete')
>>> r = httpx.head('https://httpbin.org/get')
>>> r = httpx.options('https://httpbin.org/get')
```

## Passing Parameters in URLs

To include URL query parameters in the request, use the `params` keyword:

```pycon
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> r = httpx.get('https://httpbin.org/get', params=params)
```

To see how the values get encoding into the URL string, we can inspect the
resulting URL that was used to make the request:

```pycon
>>> r.url
URL('https://httpbin.org/get?key2=value2&key1=value1')
```

You can also pass a list of items as a value:

```pycon
>>> params = {'key1': 'value1', 'key2': ['value2', 'value3']}
>>> r = httpx.get('https://httpbin.org/get', params=params)
>>> r.url
URL('https://httpbin.org/get?key1=value1&key2=value2&key2=value3')
```

## Response Content

HTTPX will automatically handle decoding the response content into Unicode text.

```pycon
>>> r = httpx.get('https://www.example.org/')
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

You can inspect what encoding will be used to decode the response.

```pycon
>>> r.encoding
'UTF-8'
```

In some cases the response may not contain an explicit encoding, in which case HTTPX
will attempt to automatically determine an encoding to use. This defaults to
UTF-8, but also includes robust fallback behaviour for handling ascii,
iso-8859-1 and windows 1252 encodings.

```pycon
>>> r.encoding
None
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```


If you need to override the standard behaviour and explicitly set the encoding to
use, then you can do that too.

```pycon
>>> r.encoding = 'ISO-8859-1'
```

## Binary Response Content

The response content can also be accessed as bytes, for non-text responses:

```pycon
>>> r.content
b'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

Any `gzip` and `deflate` HTTP response encodings will automatically
be decoded for you. If `brotlipy` is installed, then the `brotli` response
encoding will also be supported.

For example, to create an image from binary data returned by a request, you can use the following code:

```pycon
>>> from PIL import Image
>>> from io import BytesIO
>>> i = Image.open(BytesIO(r.content))
```

## JSON Response Content

Often Web API responses will be encoded as JSON.

```pycon
>>> r = httpx.get('https://api.github.com/events')
>>> r.json()
[{u'repository': {u'open_issues': 0, u'url': 'https://github.com/...' ...  }}]
```

## Custom Headers

To include additional headers in the outgoing request, use the `headers` keyword argument:

```pycon
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> r = httpx.get(url, headers=headers)
```

## Sending Form Encoded Data

Some types of HTTP requests, such as `POST` and `PUT` requests, can include data
in the request body. One common way of including that is as form-encoded data,
which is used for HTML forms.

```pycon
>>> data = {'key1': 'value1', 'key2': 'value2'}
>>> r = httpx.post("https://httpbin.org/post", data=data)
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

Form encoded data can also include multiple values from a given key.

```pycon
>>> data = {'key1': ['value1', 'value2']}
>>> r = httpx.post("https://httpbin.org/post", data=data)
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

```pycon
>>> files = {'upload-file': open('report.xls', 'rb')}
>>> r = httpx.post("https://httpbin.org/post", files=files)
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

```pycon
>>> files = {'upload-file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel')}
>>> r = httpx.post("https://httpbin.org/post", files=files)
>>> print(r.text)
{
  ...
  "files": {
    "upload-file": "<... binary content ...>"
  },
  ...
}
```

If you need to include non-file data fields in the multipart form, use the `data=...` parameter:

```pycon
>>> data = {'message': 'Hello, world!'}
>>> files = {'file': open('report.xls', 'rb')}
>>> r = httpx.post("https://httpbin.org/post", data=data, files=files)
>>> print(r.text)
{
  ...
  "files": {
    "file": "<... binary content ...>"
  },
  "form": {
    "message": "Hello, world!",
  },
  ...
}
```

## Sending JSON Encoded Data

Form encoded data is okay if all you need is a simple key-value data structure.
For more complicated data structures you'll often want to use JSON encoding instead.

```pycon
>>> data = {'integer': 123, 'boolean': True, 'list': ['a', 'b', 'c']}
>>> r = httpx.post("https://httpbin.org/post", json=data)
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

For other encodings, you should use the `content=...` parameter, passing
either a `bytes` type or a generator that yields `bytes`.

```pycon
>>> content = b'Hello, world'
>>> r = httpx.post("https://httpbin.org/post", content=content)
```

You may also want to set a custom `Content-Type` header when uploading
binary data.

## Response Status Codes

We can inspect the HTTP status code of the response:

```pycon
>>> r = httpx.get('https://httpbin.org/get')
>>> r.status_code
200
```

HTTPX also includes an easy shortcut for accessing status codes by their text phrase.

```pycon
>>> r.status_code == httpx.codes.OK
True
```

We can raise an exception for any Client or Server error responses (4xx or 5xx status codes):

```pycon
>>> not_found = httpx.get('https://httpbin.org/status/404')
>>> not_found.status_code
404
>>> not_found.raise_for_status()
Traceback (most recent call last):
  File "/Users/tomchristie/GitHub/encode/httpcore/httpx/models.py", line 837, in raise_for_status
    raise HTTPStatusError(message, response=self)
httpx._exceptions.HTTPStatusError: 404 Client Error: Not Found for url: https://httpbin.org/status/404
For more information check: https://httpstatuses.com/404
```

Any successful response codes will simply return `None` rather than raising an exception.

```pycon
>>> r.raise_for_status()
```

## Response Headers

The response headers are available as a dictionary-like interface.

```pycon
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

```pycon
>>> r.headers['Content-Type']
'application/json'

>>> r.headers.get('content-type')
'application/json'
```

Multiple values for a single response header are represented as a single comma-separated value, as per [RFC 7230](https://tools.ietf.org/html/rfc7230#section-3.2):

> A recipient MAY combine multiple header fields with the same field name into one “field-name: field-value” pair, without changing the semantics of the message, by appending each subsequent field-value to the combined field value in order, separated by a comma.

## Streaming Responses

For large downloads you may want to use streaming responses that do not load the entire response body into memory at once.

You can stream the binary content of the response...

```pycon
>>> with httpx.stream("GET", "https://www.example.com") as r:
...     for data in r.iter_bytes():
...         print(data)
```

Or the text of the response...

```pycon
>>> with httpx.stream("GET", "https://www.example.com") as r:
...     for text in r.iter_text():
...         print(text)
```

Or stream the text, on a line-by-line basis...

```pycon
>>> with httpx.stream("GET", "https://www.example.com") as r:
...     for line in r.iter_lines():
...         print(line)
```

HTTPX will use universal line endings, normalising all cases to `\n`.

In some cases you might want to access the raw bytes on the response without applying any HTTP content decoding. In this case any content encoding that the web server has applied such as `gzip`, `deflate`, or `brotli` will not be automatically decoded.

```pycon
>>> with httpx.stream("GET", "https://www.example.com") as r:
...     for chunk in r.iter_raw():
...         print(chunk)
```

If you're using streaming responses in any of these ways then the `response.content` and `response.text` attributes will not be available, and will raise errors if accessed. However you can also use the response streaming functionality to conditionally load the response body:

```pycon
>>> with httpx.stream("GET", "https://www.example.com") as r:
...     if r.headers['Content-Length'] < TOO_LONG:
...         r.read()
...         print(r.text)
```

## Cookies

Any cookies that are set on the response can be easily accessed:

```pycon
>>> r = httpx.get('http://httpbin.org/cookies/set?chocolate=chip', allow_redirects=False)
>>> r.cookies['chocolate']
'chip'
```

To include cookies in an outgoing request, use the `cookies` parameter:

```pycon
>>> cookies = {"peanut": "butter"}
>>> r = httpx.get('http://httpbin.org/cookies', cookies=cookies)
>>> r.json()
{'cookies': {'peanut': 'butter'}}
```

Cookies are returned in a `Cookies` instance, which is a dict-like data structure
with additional API for accessing cookies by their domain or path.

```pycon
>>> cookies = httpx.Cookies()
>>> cookies.set('cookie_on_domain', 'hello, there!', domain='httpbin.org')
>>> cookies.set('cookie_off_domain', 'nope.', domain='example.org')
>>> r = httpx.get('http://httpbin.org/cookies', cookies=cookies)
>>> r.json()
{'cookies': {'cookie_on_domain': 'hello, there!'}}
```

## Redirection and History

By default, HTTPX will follow redirects for all HTTP methods.


The `history` property of the response can be used to inspect any followed redirects.
It contains a list of any redirect responses that were followed, in the order
in which they were made.

For example, GitHub redirects all HTTP requests to HTTPS.

```pycon
>>> r = httpx.get('http://github.com/')
>>> r.url
URL('https://github.com/')
>>> r.status_code
200
>>> r.history
[<Response [301 Moved Permanently]>]
```

You can modify the default redirection handling with the allow_redirects parameter:

```pycon
>>> r = httpx.get('http://github.com/', allow_redirects=False)
>>> r.status_code
301
>>> r.history
[]
```

## Timeouts

HTTPX defaults to including reasonable timeouts for all network operations,
meaning that if a connection is not properly established then it should always
raise an error rather than hanging indefinitely.

The default timeout for network inactivity is five seconds. You can modify the
value to be more or less strict:

```pycon
>>> httpx.get('https://github.com/', timeout=0.001)
```

You can also disable the timeout behavior completely...

```pycon
>>> httpx.get('https://github.com/', timeout=None)
```

For advanced timeout management, see [Timeout fine-tuning](advanced.md#fine-tuning-the-configuration).

## Authentication

HTTPX supports Basic and Digest HTTP authentication.

To provide Basic authentication credentials, pass a 2-tuple of
plaintext `str` or `bytes` objects as the `auth` argument to the request
functions:

```pycon
>>> httpx.get("https://example.com", auth=("my_user", "password123"))
```

To provide credentials for Digest authentication you'll need to instantiate
a `DigestAuth` object with the plaintext username and password as arguments.
This object can be then passed as the `auth` argument to the request methods
as above:

```pycon
>>> auth = httpx.DigestAuth("my_user", "password123")
>>> httpx.get("https://example.com", auth=auth)
<Response [200 OK]>
```
