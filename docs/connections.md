# Connections

The mechanics of sending HTTP requests is dealt with by the `ConnectionPool` and `Connection` classes.

We can introspect a `Client` instance to get some visibility onto the state of the connection pool.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.Client() as cli
>>>     urls = [
...         "https://www.wikipedia.org/",
...         "https://www.theguardian.com/",
...         "https://news.ycombinator.com/",
...     ]
...     for url in urls:
...         cli.get(url)
...      print(cli.transport)
...      # <ConnectionPool [3 idle]>
...      print(cli.transport.connections)
...      # [
...      #     <Connection "https://www.wikipedia.org/" IDLE>,
...      #     <Connection "https://www.theguardian.com/" IDLE>,
...      #     <Connection "https://news.ycombinator.com/" IDLE>,
...      # ]
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.Client() as cli
>>>     urls = [
...         "https://www.wikipedia.org/",
...         "https://www.theguardian.com/",
...         "https://news.ycombinator.com/",
...     ]
...     for url in urls:
...         await cli.get(url)
...      print(cli.transport)
...      # <ConnectionPool [3 idle]>
...      print(cli.transport.connections)
...      # [
...      #     <Connection "https://www.wikipedia.org/" IDLE>,
...      #     <Connection "https://www.theguardian.com/" IDLE>,
...      #     <Connection "https://news.ycombinator.com/" IDLE>,
...      # ]
```

---

## Understanding the stack

The `Client` class is responsible for handling redirects and cookies.

It also ensures that outgoing requests include a default set of headers such as `User-Agent` and `Accept-Encoding`.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.Client() as cli:
>>>     r = cli.request("GET", "https://www.example.com/")
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.Client() as cli:
>>>     r = await cli.request("GET", "https://www.example.com/")
```

The `Client` class sends requests using a `ConnectionPool`, which is responsible for managing a pool of HTTP connections. This ensures quicker and more efficient use of resources than opening and closing a TCP connection with each request. The connection pool also handles HTTP proxying if required.

A single connection pool is able to handle multiple concurrent requests, with locking in place to ensure that the pool does not become over-saturated.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.ConnectionPool() as pool:
>>>     r = pool.request("GET", "https://www.example.com/")
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.ConnectionPool() as pool:
>>>     r = await pool.request("GET", "https://www.example.com/")
```

Individual HTTP connections can be managed directly with the `Connection` class. A single connection can only handle requests sequentially. Locking is provided to ensure that requests are strictly queued sequentially.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.open_connection("https://www.example.com/") as conn:
>>>     r = conn.request("GET", "/")
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.open_connection("https://www.example.com/") as conn:
>>>     r = await conn.request("GET", "/")
```

The `NetworkBackend` is responsible for managing the TCP stream, providing a raw byte-wise interface onto the underlying socket.

---

## ConnectionPool

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> pool = httpx.ConnectionPool()
>>> pool
<ConnectionPool [0 active]>
```

```{ .python .ahttpx .hidden }
>>> pool = ahttpx.ConnectionPool()
>>> pool
<ConnectionPool [0 active]>
```

### `.request(method, url, headers=None, content=None)`

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.ConnectionPool() as pool:
>>>     res = pool.request("GET", "https://www.example.com")
>>>     res, pool
<Response [200 OK]>, <ConnectionPool [1 idle]>
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.ConnectionPool() as pool:
>>>     res = await pool.request("GET", "https://www.example.com")
>>>     res, pool
<Response [200 OK]>, <ConnectionPool [1 idle]>
```

### `.stream(method, url, headers=None, content=None)`

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.ConnectionPool() as pool:
>>>     with pool.stream("GET", "https://www.example.com") as res:
>>>         res, pool
<Response [200 OK]>, <ConnectionPool [1 active]>
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.ConnectionPool() as pool:
>>>     async with await pool.stream("GET", "https://www.example.com") as res:
>>>         res, pool
<Response [200 OK]>, <ConnectionPool [1 active]>
```

### `.send(request)`

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.ConnectionPool() as pool:
>>>     req = httpx.Request("GET", "https://www.example.com")
>>>     with pool.send(req) as res:
>>>         res.read()
>>>     res, pool
<Response [200 OK]>, <ConnectionPool [1 idle]>
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.ConnectionPool() as pool:
>>>     req = ahttpx.Request("GET", "https://www.example.com")
>>>     async with await pool.send(req) as res:
>>>         await res.read()
>>>     res, pool
<Response [200 OK]>, <ConnectionPool [1 idle]>
```

### `.close()`

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.ConnectionPool() as pool:
>>>     pool.close()
<ConnectionPool [0 active]>
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.ConnectionPool() as pool:
>>>     await pool.close()
<ConnectionPool [0 active]>
```

---

## Connection

*TODO*

---

## Protocol upgrades

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
with httpx.open_connection("https://www.example.com/") as conn:
    with conn.upgrade("GET", "/feed", {"Upgrade": "WebSocket"}) as stream:
        ...
```

```{ .python .ahttpx .hidden }
async with await ahttpx.open_connection("https://www.example.com/") as conn:
    async with await conn.upgrade("GET", "/feed", {"Upgrade": "WebSocket"}) as stream:
        ...
```

`<Connection “https://www.example.com/feed” WEBSOCKET>`

## Proxy `CONNECT` requests

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
with httpx.open_connection("http://127.0.0.1:8080") as conn:
    with conn.upgrade("CONNECT", "www.encode.io:443") as stream:
        stream.start_tls(ctx, hostname="www.encode.io")
        ...
```

```{ .python .ahttpx .hidden }
async with await ahttpx.open_connection("http://127.0.0.1:8080") as conn:
    async with await conn.upgrade("CONNECT", "www.encode.io:443") as stream:
        await stream.start_tls(ctx, hostname="www.encode.io")
        ...
```

`<Connection "https://www.encode.io" VIA “http://127.0.0.1:8080” CONNECT>`

---

*Describe the `Transport` interface.*

---

<span class="link-prev">← [Streams](streams.md)</span>
<span class="link-next">[Parsers](parsers.md) →</span>
<span>&nbsp;</span>
