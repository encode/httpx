# Clients

HTTP requests are sent by using a `Client` instance. Client instances are thread safe interfaces that maintain a pool of HTTP connections.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> cli = httpx.Client()
>>> cli
<Client [0 active]>
```

```{ .python .ahttpx .hidden }
>>> cli = ahttpx.Client()
>>> cli
<Client [0 active]>
```

The client representation provides an indication of how many connections are currently in the pool.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> r = cli.get("https://www.example.com")
>>> r = cli.get("https://www.wikipedia.com")
>>> r = cli.get("https://www.theguardian.com/uk")
>>> cli
<Client [0 active, 3 idle]>
```

```{ .python .ahttpx .hidden }
>>> r = await cli.get("https://www.example.com")
>>> r = await cli.get("https://www.wikipedia.com")
>>> r = await cli.get("https://www.theguardian.com/uk")
>>> cli
<Client [0 active, 3 idle]>
```

The connections in the pool can be explicitly closed, using the `close()` method...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> cli.close()
>>> cli
<Client [0 active]>
```

```{ .python .ahttpx .hidden }
>>> await cli.close()
>>> cli
<Client [0 active]>
```

Client instances support being used in a context managed scope. You can use this style to enforce properly scoped resources, ensuring that the connection pool is cleanly closed when no longer required.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.Client() as cli:
...     r = cli.get("https://www.example.com")
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.Client() as cli:
...     r = await cli.get("https://www.example.com")
```

It is important to scope the use of client instances as widely as possible.

Typically you should have a single client instance that is used throughout the lifespan of your application. This ensures that connection pooling is maximised, and minmises unneccessary reloading of SSL certificate stores.

The recommened usage is to *either* a have single global instance created at import time, *or* a single context scoped instance that is passed around wherever it is required.

## Setting a base URL

Client instances can be configured with a base URL that is used when constructing requests...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.Client(url="https://www.httpbin.org") as cli:
>>>     r = cli.get("/json")
>>>     print(r)
<Response [200 OK]>
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.Client(url="https://www.httpbin.org") as cli:
>>>     r = cli.get("/json")
>>>     print(r)
<Response [200 OK]>
```

## Setting client headers

Client instances include a set of headers that are used on every outgoing request.

The default headers are:

* `Accept: */*` - Indicates to servers that any media type may be returned.
* `Accept-Encoding: gzip` - Indicates to servers that gzip compression may be used on responses.
* `Connection: keep-alive` - Indicates that HTTP/1.1 connections should be reused over multiple requests.
* `User-Agent: python-httpx/1.0` - Identify the client as `httpx`.

You can override this behavior by explicitly specifying the default headers...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> headers = {"User-Agent": "dev", "Accept-Encoding": "gzip"}
>>> with httpx.Client(headers=headers) as cli:
>>>     r = cli.get("https://www.example.com/")
```

```{ .python .ahttpx .hidden }
>>> headers = {"User-Agent": "dev", "Accept-Encoding": "gzip"}
>>> async with ahttpx.Client(headers=headers) as cli:
>>>     r = await cli.get("https://www.example.com/")
```

## Configuring the connection pool

The connection pool used by the client can be configured in order to customise the SSL context, the maximum number of concurrent connections, or the network backend.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> # Setup an SSL context to allow connecting to improperly configured SSL.
>>> no_verify = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
>>> no_verify.check_hostname = False
>>> no_verify.verify_mode = ssl.CERT_NONE
>>> # Instantiate a client with our custom SSL context.
>>> pool = httpx.ConnectionPool(ssl_context=no_verify)
>>> with httpx.Client(transport=pool) as cli:
>>>     ...
```

```{ .python .ahttpx .hidden }
>>> # Setup an SSL context to allow connecting to improperly configured SSL.
>>> no_verify = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
>>> no_verify.check_hostname = False
>>> no_verify.verify_mode = ssl.CERT_NONE
>>> # Instantiate a client with our custom SSL context.
>>> pool = ahttpx.ConnectionPool(ssl_context=no_verify)
>>> async with ahttpx.Client(transport=pool) as cli:
>>>     ...
```

## Sending requests

* `.request()` - Send an HTTP request, reading the response to completion.
* `.stream()` - Send an HTTP request, streaming the response.

Shortcut methods...

* `.get()` - Send an HTTP `GET` request.
* `.post()` - Send an HTTP `POST` request.
* `.put()` - Send an HTTP `PUT` request.
* `.delete()` - Send an HTTP `DELETE` request.

---

## Transports

By default requests are sent using the `ConnectionPool` class. Alternative implementations for sending requests can be created by subclassing the `Transport` interface.

For example, a mock transport class that doesn't make any network requests and instead always returns a fixed response.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
class MockTransport(httpx.Transport):
    def __init__(self, response):
        self._response = response

    @contextlib.contextmanager
    def send(self, request):
        yield response

    def close(self):
        pass

response = httpx.Response(200, content=httpx.Text('Hello, world'))
transport = MockTransport(response=response)
with httpx.Client(transport=transport) as cli:
    r = cli.get('https://www.example.com')
    print(r)
```

```{ .python .ahttpx .hidden }
class MockTransport(ahttpx.Transport):
    def __init__(self, response):
        self._response = response

    @contextlib.contextmanager
    def send(self, request):
        yield response

    def close(self):
        pass

response = ahttpx.Response(200, content=httpx.Text('Hello, world'))
transport = MockTransport(response=response)
async with ahttpx.Client(transport=transport) as cli:
    r = await cli.get('https://www.example.com')
    print(r)
```

---

## Middleware

In addition to maintaining an HTTP connection pool, client instances are responsible for two other pieces of functionality...

* Dealing with HTTP redirects.
* Maintaining an HTTP cookie store.

### `RedirectMiddleware`

Wraps a transport class, adding support for HTTP redirect handling.

### `CookieMiddleware`

Wraps a transport class, adding support for HTTP cookie persistence.

---

## Custom client implementations

The `Client` implementation in `httpx` is intentionally lightweight.

If you're working with a large codebase you might want to create a custom client implementation in order to constrain the types of request that are sent.

The following example demonstrates a custom API client that only exposes `GET` and `POST` requests, and always uses JSON payloads.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
class APIClient:
    def __init__(self):
        self.url = httpx.URL('https://www.example.com')
        self.headers = httpx.Headers({
            'Accept-Encoding': 'gzip',
            'Connection': 'keep-alive',
            'User-Agent': 'dev'
        })
        self.via = httpx.RedirectMiddleware(httpx.ConnectionPool())

    def get(self, path: str) -> Response:
        request = httpx.Request(
            method="GET",
            url=self.url.join(path),
            headers=self.headers,
        )
        with self.via.send(request) as response:
            response.read()
        return response

    def post(self, path: str, payload: Any) -> httpx.Response:
        request = httpx.Request(
            method="POST",
            url=self.url.join(path),
            headers=self.headers,
            content=httpx.JSON(payload),
        )
        with self.via.send(request) as response:
            response.read()
        return response
```

```{ .python .ahttpx .hidden }
class APIClient:
    def __init__(self):
        self.url = ahttpx.URL('https://www.example.com')
        self.headers = ahttpx.Headers({
            'Accept-Encoding': 'gzip',
            'Connection': 'keep-alive',
            'User-Agent': 'dev'
        })
        self.via = ahttpx.RedirectMiddleware(ahttpx.ConnectionPool())

    async def get(self, path: str) -> Response:
        request = ahttpx.Request(
            method="GET",
            url=self.url.join(path),
            headers=self.headers,
        )
        async with self.via.send(request) as response:
            await response.read()
        return response

    async def post(self, path: str, payload: Any) -> ahttpx.Response:
        request = ahttpx.Request(
            method="POST",
            url=self.url.join(path),
            headers=self.headers,
            content=httpx.JSON(payload),
        )
        async with self.via.send(request) as response:
            await response.read()
        return response
```

You can expand on this pattern to provide behavior such as request or response schema validation, consistent timeouts, or standardised logging and exception handling.

---

<span class="link-prev">← [Quickstart](quickstart.md)</span>
<span class="link-next">[Servers](servers.md) →</span>
<span>&nbsp;</span>
