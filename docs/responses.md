# Responses

The core elements of an HTTP response are the `status_code`, `headers` and `body`.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> resp = httpx.Response(200, headers={'Content-Type': 'text/plain'}, content=b'hello, world')
>>> resp
<Response [200 OK]>
>>> resp.status_code
200
>>> resp.headers
<Headers {'Content-Type': 'text/html'}>
>>> resp.body
b'hello, world'
```

```{ .python .ahttpx .hidden }
>>> resp = ahttpx.Response(200, headers={'Content-Type': 'text/plain'}, content=b'hello, world')
>>> resp
<Response [200 OK]>
>>> resp.status_code
200
>>> resp.headers
<Headers {'Content-Type': 'text/html'}>
>>> resp.body
b'hello, world'
```

## Working with the response headers

The following headers have automatic behavior with `Response` instances...

* `Content-Length` - Responses including a response body must always include either a `Content-Length` header or a `Transfer-Encoding: chunked` header. This header is automatically populated if `content` is not `None` and the content is a known size.
* `Transfer-Encoding` - Responses automatically include a `Transfer-Encoding: chunked` header if `content` is not `None` and the content is an unkwown size.
* `Content-Type` - Responses automatically include a `Content-Type` header if `content` is set using the [Content Type] API.

## Working with content types

Including HTML content...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> content = httpx.HTML('<html><head>...</head><body>...</body></html>')
>>> response = httpx.Response(200, content=content)
```

```{ .python .ahttpx .hidden }
>>> content = ahttpx.HTML('<html><head>...</head><body>...</body></html>')
>>> response = ahttpx.Response(200, content=content)
```

Including plain text content...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> content = httpx.Text('hello, world')
>>> response = httpx.Response(200, content=content)
```

```{ .python .ahttpx .hidden }
>>> content = ahttpx.Text('hello, world')
>>> response = ahttpx.Response(200, content=content)
```

Including JSON data...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> content = httpx.JSON({'message': 'hello, world'})
>>> response = httpx.Response(200, content=content)
```

```{ .python .ahttpx .hidden }
>>> content = ahttpx.JSON({'message': 'hello, world'})
>>> response = ahttpx.Response(200, content=content)
```

Including content from a file...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> content = httpx.File('index.html')
>>> with httpx.Response(200, content=content) as response:
...     pass
```

```{ .python .ahttpx .hidden }
>>> content = ahttpx.File('index.html')
>>> async with ahttpx.Response(200, content=content) as response:
...     pass
```

## Accessing response content

...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> response.body
```

```{ .python .ahttpx .hidden }
>>> response.body
```

...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> response.text
...
```

```{ .python .ahttpx .hidden }
>>> response.text
...
```

---

<span class="link-prev">← [Requests](requests.md)</span>
<span class="link-next">[URLs](urls.md) →</span>
<span>&nbsp;</span>
