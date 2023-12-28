# Building requests

The `httpx.Client()` instance includes a few configuration options that control how outgoing HTTP requests are instantiated.

## Request configuration

### Base URL

```pycon
>>> client = httpx.Client(base_url="https://www.example.com")
>>> response = client.get("/path")
>>> response.request.url
httpx.URL("https://www.example.com/path")
```

### Params

```pycon
>>> client = httpx.Client(params={"token": "text"})
>>> response = client.get("https://www.example.com")
>>> response.request.url
httpx.URL("https://www.example.com/?token=text")
```

### Headers

The default headers included with all outgoing requests are...

* `Accept`. Defaults to `*/*`, indicating that any media type may be returned by the server.
* `Accept-Encoding`. Defaults to either `'gzip, deflate'` or `'gzip, deflate, br'`, depending on if brotli support is enabled. Indicates the available compressions that the server may use for the response.
* `Connection`. Defaults to `"keep-alive"`, indicating that the server should reuse HTTP/1.1 connections between requests.
* `User-Agent`. Defaults to `"python-httpx/{version}"`.

In addition requests will automatically include a `Host` header, and optionally a `Content-Length` or `Transfer-Encoding` header. However these are determined on a per-request basis and are not part of the client configuration.

...

```pycon
>>> client = httpx.Client()
>>> print(client.headers)
...
```

```pycon
>>> client = httpx.Client(headers={"User-Agent": "custom"})
>>> print(client.headers)
...
```

```pycon
>>> client = httpx.Client()
>>> del client.headers["User-Agent"]
>>> print(client.headers)
...
```

## Building Requests

Client instances provide an API that allows us to seperate out the instantiation of the outgoing `httpx.Request` instance, and the send operation.

```pycon
>>> request = client.build_request("GET", "https://www.example.com")
>>> print(request.url)
...
>>> print(request.headers)
...
>>> response = client.send(request)
>>> print(response)
...
```

### `Client.build_request()`

**TODO**

### `Client.send()`

**TODO**

### Instantiating requests directly

In the following example we're instantiating and sending request directly here, instead of using `client.build_request()`.
We need to take care if we use this approach. In particular note the following:

* The default `Accept`, `Accept-Encoding`, `Connection`, and `User-Agent` headers will not be included, unless set explicitly.
* No client cookies will be included on the request.
* Any client timeout configuration will not be applied, unless set directly using the request `"timeout"` extension.

```pycon
>>> # This isn't a recommend way to handle sending requests, see above.
>>> request = httpx.Request("GET", "https://www.example.com", headers={"Connection": "keep-alive"})
>>> client = httpx.Client()
>>> client.send(request)
```