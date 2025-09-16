# Requests

The core elements of an HTTP request are the `method`, `url`, `headers` and `body`.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> req = httpx.Request('GET', 'https://www.example.com/')
>>> req
<Request [GET 'https://www.example.com/']>
>>> req.method
'GET'
>>> req.url
<URL 'https://www.example.com/'>
>>> req.headers
<Headers {'Host': 'www.example.com'}>
>>> req.body
b''
```

```{ .python .ahttpx .hidden }
>>> req = ahttpx.Request('GET', 'https://www.example.com/')
>>> req
<Request [GET 'https://www.example.com/']>
>>> req.method
'GET'
>>> req.url
<URL 'https://www.example.com/'>
>>> req.headers
<Headers {'Host': 'www.example.com'}>
>>> req.body
b''
```

## Working with the request headers

The following headers have automatic behavior with `Requests` instances...

* `Host` - A `Host` header must always be included on a request. This header is automatically populated from the `url`, using the `url.netloc` property.
* `Content-Length` - Requests including a request body must always include either a `Content-Length` header or a `Transfer-Encoding: chunked` header. This header is automatically populated if `content` is not `None` and the content is a known size.
* `Transfer-Encoding` - Requests automatically include a `Transfer-Encoding: chunked` header if `content` is not `None` and the content is an unkwown size.
* `Content-Type` - Requests automatically include a `Content-Type` header if `content` is set using the [Content Type] API.

## Working with the request body

Including binary data directly...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> headers = {'Content-Type': 'application/json'}
>>> content = json.dumps(...)
>>> httpx.Request('POST', 'https://echo.encode.io/', content=content)
```

```{ .python .ahttpx .hidden }
>>> headers = {'Content-Type': 'application/json'}
>>> content = json.dumps(...)
>>> ahttpx.Request('POST', 'https://echo.encode.io/', content=content)
```

## Working with content types

Including JSON request content...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> data = httpx.JSON(...)
>>> httpx.Request('POST', 'https://echo.encode.io/', content=data)
```

```{ .python .ahttpx .hidden }
>>> data = ahttpx.JSON(...)
>>> ahttpx.Request('POST', 'https://echo.encode.io/', content=data)
```

Including form encoded request content...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> data = httpx.Form(...)
>>> httpx.Request('PUT', 'https://echo.encode.io/', content=data)
```

```{ .python .ahttpx .hidden }
>>> data = ahttpx.Form(...)
>>> ahttpx.Request('PUT', 'https://echo.encode.io/', content=data)
```

Including multipart file uploads...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = httpx.MultiPart(form={...}, files={...})
>>> with httpx.Request('POST', 'https://echo.encode.io/', content=form) as req:
>>>     req.headers
{...}
>>>     req.stream
<MultiPartStream [0% of ...MB]>
```

```{ .python .ahttpx .hidden }
>>> form = ahttpx.MultiPart(form={...}, files={...})
>>> async with ahttpx.Request('POST', 'https://echo.encode.io/', content=form) as req:
>>>     req.headers
{...}
>>>     req.stream
<MultiPartStream [0% of ...MB]>
```

Including direct file uploads...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> file = httpx.File('upload.json')
>>> with httpx.Request('POST', 'https://echo.encode.io/', content=file) as req:
>>>     req.headers
{...}
>>>     req.stream
<FileStream [0% of ...MB]>
```

```{ .python .ahttpx .hidden }
>>> file = ahttpx.File('upload.json')
>>> async with ahttpx.Request('POST', 'https://echo.encode.io/', content=file) as req:
>>>     req.headers
{...}
>>>     req.stream
<FileStream [0% of ...MB]>
```

## Accessing request content

*In progress...*

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> data = request.json()
```

```{ .python .ahttpx .hidden }
>>> data = await request.json()
```

...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = request.form()
```

```{ .python .ahttpx .hidden }
>>> form = await request.form()
```

...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> files = request.files()
```

```{ .python .ahttpx .hidden }
>>> files = await request.files()
```

---

<span class="link-prev">← [Servers](servers.md)</span>
<span class="link-next">[Responses](responses.md) →</span>
<span>&nbsp;</span>
