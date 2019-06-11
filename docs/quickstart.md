# QuickStart

First start by importing HTTP3:

```
>>> import http3
```

Now, let’s try to get a webpage. For this example, let’s get GitHub’s public timeline:

```python
>>> r = http3.get('https://api.github.com/events')
```

Similarly, to make an HTTP POST request:

```python
>>> r = http3.post('https://httpbin.org/post', data={'key': 'value'})
```

The PUT, DELETE, HEAD, and OPTIONS requests all follow the same style:

```python
>>> r = http3.put('https://httpbin.org/put', data={'key': 'value'})
>>> r = http3.delete('https://httpbin.org/delete')
>>> r = http3.head('https://httpbin.org/get')
>>> r = http3.options('https://httpbin.org/get')
```

## Passing Parameters in URLs

To include URL query parameters in the request, use the `params` keyword:

```python
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> r = http3.get('https://httpbin.org/get', params=params)
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
>>> r = http3.get('https://httpbin.org/get', params=params)
>>> r.url
URL('https://httpbin.org/get?key1=value1&key2=value2&key2=value3')
```

## Response Content

HTTP3 will automatically handle decoding the response content into unicode text.

```python
>>> r = http3.get('https://www.example.org/')
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
>>> r = http3.get('https://api.github.com/events')
>>> r.json()
[{u'repository': {u'open_issues': 0, u'url': 'https://github.com/...' ...  }}]
```

## Custom Headers

To include additional headers in the outgoing request, use the `headers` keyword argument:

```python
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> r = http3.get(url, headers=headers)
```

## Sending Form Encoded Data

Some types of HTTP requests, such as `POST` and `PUT` requests, can include data
in the request body. One common way of including that is as form encoded data,
which is used for HTML forms.

```python
>>> data = {'key1': 'value1', 'key2': 'value2'}
>>> r = http3.post("https://httpbin.org/post", data=data)
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
>>> r = http3.post("https://httpbin.org/post", data=data)
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

## Sending JSON Encoded Data

Form encoded data is okay if all you need is simple key-value data structure.
For more complicated data structures you'll often want to use JSON encoding instead.

```python
>>> data = {'integer': 123, 'boolean': True, 'list': ['a', 'b', 'c']}
>>> r = http3.post("https://httpbin.org/post", json=data)
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

For other encodings you should use either a `bytes` type, or a generator
that yields `bytes`.

You'll probably also want to set a custom `Content-Type` header when uploading
binary data.

## Response Status Codes

We can inspect the HTTP status code of the response:

```python
>>> r = http3.get('https://httpbin.org/get')
>>> r.status_code
<StatusCode.OK: 200>
```

The status code is an integer enum, meaning that the Python representation gives
use some descriptive information, but the value itself can be used as a regular integer.

```python
>>> r.status_code == 200
True
```

HTTP3 also includes an easy shortcut for accessing status codes by their text phrase.

```python
>>> r.status_code == requests.codes.OK
True
```

We can raise an exception for any Client or Server error responses (4xx or 5xx status codes):

```python
>>> not_found = http3.get('https://httpbin.org/status/404')
>>> not_found.status_code
<StatusCode.NOT_FOUND: 404>
>>> not_found.raise_for_status()
Traceback (most recent call last):
  File "/Users/tomchristie/GitHub/encode/httpcore/http3/models.py", line 776, in raise_for_status
    raise HttpError(message)
http3.exceptions.HttpError: 404 Not Found
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

Multiple values for a single response header are represented as a single comma separated
value, as per [RFC 7230](https://tools.ietf.org/html/rfc7230#section-3.2):

> A recipient MAY combine multiple header fields with the same field name into one “field-name: field-value” pair, without changing the semantics of the message, by appending each subsequent field value to the combined field value in order, separated by a comma.
