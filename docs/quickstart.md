# QuickStart

Install using ...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .shell .httpx }
$ pip install --pre httpx
```

```{ .shell .ahttpx .hidden }
$ pip install --pre ahttpx
```

First, start by importing `httpx`...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> import httpx
```

```{ .python .ahttpx .hidden }
>>> import ahttpx
```

Now, let’s try to get a webpage.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r = httpx.get('https://httpbin.org/get')
>>> r
<Response [200 OK]>
```

```{ .python .ahttpx .hidden }
>>> r = await ahttpx.get('https://httpbin.org/get')
>>> r
<Response [200 OK]>
```

To make an HTTP `POST` request, including some content...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = httpx.Form({'key': 'value'})
>>> r = httpx.post('https://httpbin.org/post', content=form)
```

```{ .python .ahttpx .hidden }
>>> form = httpx.Form({'key': 'value'})
>>> r = await ahttpx.post('https://httpbin.org/post', content=form)
```

Shortcut methods for `PUT`, `PATCH`, and `DELETE` requests follow the same style...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r = httpx.put('https://httpbin.org/put', content=form)
>>> r = httpx.patch('https://httpbin.org/patch', content=form)
>>> r = httpx.delete('https://httpbin.org/delete')
```

```{ .python .ahttpx .hidden }
>>> r = await ahttpx.put('https://httpbin.org/put', content=form)
>>> r = await ahttpx.patch('https://httpbin.org/patch', content=form)
>>> r = await ahttpx.delete('https://httpbin.org/delete')
```

## Passing Parameters in URLs

To include URL query parameters in the request, construct a URL using the `params` keyword...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> url = httpx.URL('https://httpbin.org/get', params=params)
>>> r = httpx.get(url)
```

```{ .python .ahttpx .hidden }
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> url = ahttpx.URL('https://httpbin.org/get', params=params)
>>> r = await ahttpx.get(url)
```

You can also pass a list of items as a value...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = {'key1': 'value1', 'key2': ['value2', 'value3']}
>>> url = httpx.URL('https://httpbin.org/get', params=params)
>>> r = httpx.get(url)
```

```{ .python .ahttpx .hidden }
>>> params = {'key1': 'value1', 'key2': ['value2', 'value3']}
>>> url = ahttpx.URL('https://httpbin.org/get', params=params)
>>> r = await ahttpx.get(url)
```

## Custom Headers

To include additional headers in the outgoing request, use the `headers` keyword argument...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> url = 'https://httpbin.org/headers'
>>> headers = {'User-Agent': 'my-app/0.0.1'}
>>> r = httpx.get(url, headers=headers)
```

```{ .python .ahttpx .hidden }
>>> url = 'https://httpbin.org/headers'
>>> headers = {'User-Agent': 'my-app/0.0.1'}
>>> r = await ahttpx.get(url, headers=headers)
```

---

## Response Content

HTTPX will automatically handle decoding the response content into unicode text.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r = httpx.get('https://www.example.org/')
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

```{ .python .ahttpx .hidden }
>>> r = await ahttpx.get('https://www.example.org/')
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

## Binary Response Content

The response content can also be accessed as bytes, for non-text responses.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r.body
b'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

```{ .python .ahttpx .hidden }
>>> r.body
b'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

## JSON Response Content

Often Web API responses will be encoded as JSON.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r = httpx.get('https://httpbin.org/get')
>>> r.json()
{'args': {}, 'headers': {'Host': 'httpbin.org', 'User-Agent': 'dev', 'X-Amzn-Trace-Id': 'Root=1-679814d5-0f3d46b26686f5013e117085'}, 'origin': '21.35.60.128', 'url': 'https://httpbin.org/get'}
```

```{ .python .ahttpx .hidden }
>>> r = await ahttpx.get('https://httpbin.org/get')
>>> await r.json()
{'args': {}, 'headers': {'Host': 'httpbin.org', 'User-Agent': 'dev', 'X-Amzn-Trace-Id': 'Root=1-679814d5-0f3d46b26686f5013e117085'}, 'origin': '21.35.60.128', 'url': 'https://httpbin.org/get'}
```

---

## Sending Form Encoded Data

Some types of HTTP requests, such as `POST` and `PUT` requests, can include data in the request body. One common way of including that is as form-encoded data, which is used for HTML forms.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = httpx.Form({'key1': 'value1', 'key2': 'value2'})
>>> r = httpx.post("https://httpbin.org/post", content=form)
>>> r.json()
{
  ...
  "form": {
    "key2": "value2",
    "key1": "value1"
  },
  ...
}
```

```{ .python .ahttpx .hidden }
>>> form = ahttpx.Form({'key1': 'value1', 'key2': 'value2'})
>>> r = await ahttpx.post("https://httpbin.org/post", content=form)
>>> await r.json()
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

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = httpx.Form({'key1': ['value1', 'value2']})
>>> r = httpx.post("https://httpbin.org/post", content=form)
>>> r.json()
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

```{ .python .ahttpx .hidden }
>>> form = ahttpx.Form({'key1': ['value1', 'value2']})
>>> r = await ahttpx.post("https://httpbin.org/post", content=form)
>>> await r.json()
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

You can also upload files, using HTTP multipart encoding.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> files = httpx.Files({'upload': httpx.File('uploads/report.xls')})
>>> r = httpx.post("https://httpbin.org/post", content=files)
>>> r.json()
{
  ...
  "files": {
    "upload": "<... binary content ...>"
  },
  ...
}
```

```{ .python .ahttpx .hidden }
>>> files = ahttpx.Files({'upload': httpx.File('uploads/report.xls')})
>>> r = await ahttpx.post("https://httpbin.org/post", content=files)
>>> await r.json()
{
  ...
  "files": {
    "upload": "<... binary content ...>"
  },
  ...
}
```

If you need to include non-file data fields in the multipart form, use the `data=...` parameter:

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = {'message': 'Hello, world!'}
>>> files = {'upload': httpx.File('uploads/report.xls')}
>>> data = httpx.MultiPart(form=form, files=files)
>>> r = httpx.post("https://httpbin.org/post", content=data)
>>> r.json()
{
  ...
  "files": {
    "upload": "<... binary content ...>"
  },
  "form": {
    "message": "Hello, world!",
  },
  ...
}
```

```{ .python .ahttpx .hidden }
>>> form = {'message': 'Hello, world!'}
>>> files = {'upload': httpx.File('uploads/report.xls')}
>>> data = ahttpx.MultiPart(form=form, files=files)
>>> r = await ahttpx.post("https://httpbin.org/post", content=data)
>>> await r.json()
{
  ...
  "files": {
    "upload": "<... binary content ...>"
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

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> data = {'integer': 123, 'boolean': True, 'list': ['a', 'b', 'c']}
>>> r = httpx.post("https://httpbin.org/post", content=httpx.JSON(data))
>>> r.json()
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

```{ .python .ahttpx .hidden }
>>> data = {'integer': 123, 'boolean': True, 'list': ['a', 'b', 'c']}
>>> r = await ahttpx.post("https://httpbin.org/post", content=httpx.JSON(data))
>>> await r.json()
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

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> content = b'Hello, world'
>>> r = httpx.post("https://httpbin.org/post", content=content)
```

```{ .python .ahttpx .hidden }
>>> content = b'Hello, world'
>>> r = await ahttpx.post("https://httpbin.org/post", content=content)
```

You may also want to set a custom `Content-Type` header when uploading
binary data.

---

## Response Status Codes

We can inspect the HTTP status code of the response:

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r = httpx.get('https://httpbin.org/get')
>>> r.status_code
200
```

```{ .python .ahttpx .hidden }
>>> r = await ahttpx.get('https://httpbin.org/get')
>>> r.status_code
200
```

## Response Headers

The response headers are available as a dictionary-like interface.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r.headers
<Headers {
    'Content-Encoding': 'gzip',
    'Connection': 'close',
    'Server': 'nginx/1.0.4',
    'ETag': 'e1ca502697e5c9317743dc078f67693f',
    'Content-Type': 'application/json',
    'Content-Length': 2126,
}>
```

```{ .python .ahttpx .hidden }
>>> r.headers
<Headers {
    'Content-Encoding': 'gzip',
    'Connection': 'close',
    'Server': 'nginx/1.0.4',
    'ETag': 'e1ca502697e5c9317743dc078f67693f',
    'Content-Type': 'application/json',
    'Content-Length': 2126,
}>
```

The `Headers` data type is case-insensitive, so you can use any capitalization.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r.headers.get('Content-Type')
'application/json'

>>> r.headers.get('content-type')
'application/json'
```

```{ .python .ahttpx .hidden }
>>> r.headers.get('Content-Type')
'application/json'

>>> r.headers.get('content-type')
'application/json'
```

---

## Streaming Responses

For large downloads you may want to use streaming responses that do not load the entire response body into memory at once.

You can stream the binary content of the response...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.stream("GET", "https://www.example.com") as r:
...     for data in r.stream:
...         print(data)
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.stream("GET", "https://www.example.com") as r:
...     async for data in r.stream:
...         print(data)
```

---

<span class="link-prev">← [Home](index.md)</span>
<span class="link-next">[Clients](clients.md) →</span>
<span>&nbsp;</span>