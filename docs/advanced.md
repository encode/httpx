# Advanced Usage

## Client Instances

Using a Client instance to make requests will give you HTTP connection pooling,
will provide cookie persistence, and allows you to apply configuration across
all outgoing requests.

!!! hint
    A Client instance is equivalent to a Session instance in `requests`.

!!! note
    Starting from `httpx==0.10.0`, the default and recommended Client class is `AsyncClient`. This should help prevent breaking changes once sync support is reintroduced.

    A `Client` synonym remains for compatibility with `httpx==0.9.*` releases, but you are encouraged to migrate to `AsyncClient` as soon as possible.

### Usage

The recommended way to use a `Client` is as a context manager. This will ensure that connections are properly cleaned up when leaving the `with` block:

```python
>>> async with httpx.AsyncClient() as client:
...     r = await client.get('https://example.com')
...
>>> r
<Response [200 OK]>
```

Alternatively, you can explicitly close the connection pool without block-usage using `.aclose()`:

```python
>>> client = httpx.AsyncClient()
>>> try:
...     r = await client.get('https://example.com')
... finally:
...     await client.aclose()
...
>>> r
<Response [200 OK]>
```

Once you have a `Client`, you can use all the features documented in the [Quickstart](/quickstart) guide.

### Configuration

Clients allow you to apply configuration to all outgoing requests by passing parameters to the `Client` constructor.

For example, to apply a set of custom headers on every request:

```python
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> async with httpx.AsyncClient(headers=headers) as client:
...     r = await client.get(url)
...
>>> r.json()['headers']['User-Agent']
'my-app/0.0.1'
```

!!! note
    When you provide a parameter at both the client and request levels, one of two things can happen:

    - For headers, query parameters and cookies, the values are merged into one.
    - For all other parameters, the request-level value is used.

Additionally, `Client` accepts some parameters that aren't available at the request level.

One particularly useful parameter is `base_url`, which allows you to define a base URL to prepend to all outgoing requests:

```python
>>> async with httpx.AsyncClient(base_url='http://httpbin.org') as client:
...     r = await client.get('/headers')
...
>>> r.request.url
URL('http://httpbin.org/headers')
```

For a list of all available client-level parameters, see the [`AsyncClient` API reference](/api/#async-client).

## Calling into Python Web Apps

You can configure an `httpx` client to call directly into a Python web
application using the ASGI protocol.

This is particularly useful for two main use-cases:

* Using `httpx` as a client inside test cases.
* Mocking out external services during tests or in dev/staging environments.

Let's take this Starlette application as an example:

```python
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route


async def hello():
    return HTMLResponse("Hello World!")


app = Starlette(routes=[Route("/", hello)])
```

We can make requests directly against the application, like so:

```python
>>> import httpx
>>> async with httpx.AsyncClient(app=app) as client:
...     r = client.get('http://example/')
...     assert r.status_code == 200
...     assert r.text == "Hello World!"
```

For some more complex cases you might need to customise the ASGI dispatch. This allows you to:

* Inspect 500 error responses rather than raise exceptions by setting `raise_app_exceptions=False`.
* Mount the ASGI application at a subpath by setting `root_path`.
* Use a given client address for requests by setting `client`.

For example:

```python
# Instantiate a client that makes ASGI requests with a client IP of "1.2.3.4",
# on port 123.
dispatch = httpx.dispatch.ASGIDispatch(app=app, client=("1.2.3.4", 123))
async with httpx.AsyncClient(dispatch=dispatch) as client:
    ...
```

See [the ASGI documentation](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope) for more details on the `client` and `root_path`
keys.

## Build Request

You can use `Client.build_request()` to build a request and
make modifications before sending the request.

```python
>>> async with httpx.AsyncClient() as client:
...     req = client.build_request("OPTIONS", "https://example.com")
...     req.url.full_path = "*"  # Build an 'OPTIONS *' request for CORS
...     r = await client.send(req)
...
>>> r
<Response [200 OK]>
```

## .netrc Support

HTTPX supports .netrc file. In `trust_env=True` cases, if auth parameter is
not defined, HTTPX tries to add auth into request's header from .netrc file.

!!! note
    The NETRC file is cached across requests made by a client.
    If you need to refresh the cache (e.g. because the NETRC file has changed),
    you should create a new client or restart the interpreter.

As default `trust_env` is true. To set false:
```python
>>> await httpx.get('https://example.org/', trust_env=False)
```

If `NETRC` environment is empty, HTTPX tries to use default files.
(`~/.netrc`, `~/_netrc`)

To change `NETRC` environment:
```python
>>> import os
>>> os.environ["NETRC"] = "my_default_folder/.my_netrc"
```

.netrc file content example:
```
machine netrcexample.org
login example-username
password example-password

...
```

When using `Client` instances, `trust_env` should be set on the client itself, rather that on the request methods:

```python
client = httpx.AsyncClient(trust_env=False)
```

## Unix Domain Sockets

You can configure an `httpx` client to connect through a unix domain socket via the `uds` parameter. This is useful when making requests to a server that is bound to a socket file rather than an IP address.

Here's an example requesting the Docker Engine API:

```python
import httpx


async with httpx.AsyncClient(uds="/var/run/docker.sock") as client:
    # This request will connect through the socket file.
    resp = await client.get("http://localhost/version")
```

## HTTP Proxying

HTTPX supports setting up proxies the same way that Requests does via the `proxies` parameter.
For example to forward all HTTP traffic to `http://127.0.0.1:3080` and all HTTPS traffic
to `http://127.0.0.1:3081` your `proxies` config would look like this:

```python
>>> proxies = {
...     "http": "http://127.0.0.1:3080",
...     "https": "http://127.0.0.1:3081"
... }
>>> async with httpx.AsyncClient(proxies=proxies) as client:
...     ...
```

Proxies can be configured for a specific scheme and host, all schemes of a host,
all hosts for a scheme, or for all requests. When determining which proxy configuration
to use for a given request this same order is used.

```python
>>> proxies = {
...     "http://example.com":  "...",  # Host+Scheme
...     "all://example.com":  "...",  # Host
...     "http": "...",  # Scheme
...     "all": "...",  # All
... }
>>> async with httpx.AsyncClient(proxies=proxies) as client:
...     ...
...
>>> proxy = "..."  # Shortcut for {'all': '...'}
>>> async with httpx.AsyncClient(proxies=proxy) as client:
...     ...
```

!!! warning
    To make sure that proxies cannot read your traffic,
    and even if the proxy_url uses HTTPS, it is recommended to
    use HTTPS and tunnel requests if possible.

By default `HTTPProxy` will operate as a forwarding proxy for `http://...` requests
and will establish a `CONNECT` TCP tunnel for `https://` requests. This doesn't change
regardless of the `proxy_url` being `http` or `https`.

Proxies can be configured to have different behavior such as forwarding or tunneling all requests:

```python
proxy = httpx.HTTPProxy(
    proxy_url="https://127.0.0.1",
    proxy_mode="TUNNEL_ONLY"  # May be "TUNNEL_ONLY" or "FORWARD_ONLY". Defaults to "DEFAULT".
)
async with httpx.AsyncClient(proxies=proxy) as client:
    # This request will be tunneled instead of forwarded.
    r = await client.get("http://example.com")
```

!!! note

    Per request proxy configuration, i.e. `client.get(url, proxies=...)`,
    has not been implemented yet. To use proxies you must pass the proxy
    information at `Client` initialization.

## Timeout Configuration

HTTPX is careful to enforce timeouts everywhere by default.

The default behavior is to raise a `TimeoutException` after 5 seconds of
network inactivity.

### Setting and disabling timeouts

You can set timeouts for an individual request:

```python
# Using the top-level API:
await httpx.get('http://example.com/api/v1/example', timeout=10.0)

# Using a client instance:
async with httpx.AsyncClient() as client:
    await client.get("http://example.com/api/v1/example", timeout=10.0)
```

Or disable timeouts for an individual request:

```python
# Using the top-level API:
await httpx.get('http://example.com/api/v1/example', timeout=None)

# Using a client instance:
async with httpx.AsyncClient() as client:
    await client.get("http://example.com/api/v1/example", timeout=None)
```

### Setting a default timeout on a client

You can set a timeout on a client instance, which results in the given
`timeout` being used as the default for requests made with this client:

```python
client = httpx.AsyncClient()              # Use a default 5s timeout everywhere.
client = httpx.AsyncClient(timeout=10.0)  # Use a default 10s timeout everywhere.
client = httpx.AsyncClient(timeout=None)  # Disable all timeouts by default.
```

### Fine tuning the configuration

HTTPX also allows you to specify the timeout behavior in more fine grained detail.

There are four different types of timeouts that may occur. These are **connect**,
**read**, **write**, and **pool** timeouts.

* The **connect timeout** specifies the maximum amount of time to wait until
a connection to the requested host is established. If HTTPX is unable to connect
within this time frame, a `ConnectTimeout` exception is raised.
* The **read timeout** specifies the maximum duration to wait for a chunk of
data to be received (for example, a chunk of the response body). If HTTPX is
unable to receive data within this time frame, a `ReadTimeout` exception is raised.
* The **write timeout** specifies the maximum duration to wait for a chunk of
data to be sent (for example, a chunk of the request body). If HTTPX is unable
to send data within this time frame, a `WriteTimeout` exception is raised.
* The **pool timeout** specifies the maximum duration to wait for acquiring
a connection from the connection pool. If HTTPX is unable to acquire a connection
within this time frame, a `PoolTimeout` exception is raised. A related
configuration here is the maximum number of allowable connections in the
connection pool, which is configured by the `pool_limits`.

You can configure the timeout behavior for any of these values...

```python
# A client with a 60s timeout for connecting, and a 10s timeout elsewhere.
timeout = httpx.Timeout(10.0, connect_timeout=60.0)
client = httpx.AsyncClient(timeout=timeout)

response = await client.get('http://example.com/')
```

## Multipart file encoding

As mentioned in the [quickstart](/quickstart#sending-multipart-file-uploads)
multipart file encoding is available by passing a dictionary with the
name of the payloads as keys and either tuple of elements or a file-like object or a string as values.

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

More specifically, if a tuple is used as a value, it must have between 2 and 3 elements:

- The first element is an optional file name which can be set to `None`.
- The second element may be a file-like object or a string which will be automatically
encoded in UTF-8.
- An optional third element can be used to specify the
[MIME type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_Types)
of the file being uploaded. If not specified HTTPX will attempt to guess the MIME type based
on the file name, with unknown file extensions defaulting to "application/octet-stream".
If the file name is explicitly set to `None` then HTTPX will not include a content-type
MIME header field.

```python
>>> files = {'upload-file': (None, 'text content', 'text/plain')}
>>> r = await httpx.post("https://httpbin.org/post", files=files)
>>> print(r.text)
{
  ...
  "files": {},
  "form": {
    "upload-file": "text-content"
  },
  ...
}
```

## SSL certificates

When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

### Changing the verification defaults

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/). This is what you want in most cases, even though some advanced situations may require you to use a different set of certificates.

If you'd like to use a custom CA bundle, you can use the `verify` parameter.

```python
import httpx

r = await httpx.get("https://example.org", verify="path/to/client.pem")
```

You can also disable the SSL verification...

```python
import httpx

r = await httpx.get("https://example.org", verify=False)
```

### SSL configuration on client instances

If you're using a `Client()` instance, then you should pass any SSL settings when instantiating the client.

```python
client = httpx.AsyncClient(verify=False)
```

The `client.get(...)` method and other request methods *do not* support changing the SSL settings on a per-request basis. If you need different SSL settings in different cases you should use more that one client instance, with different settings on each. Each client will then be using an isolated connection pool with a specific fixed SSL configuration on all connections within that pool.

### Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme-cli](https://github.com/sethmlarson/trustme-cli/) to generate a pair of server key/cert files, and a client cert file.
1. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
1. Tell HTTPX to use the certificates stored in `client.pem`:

```python
>>> import httpx
>>> r = await httpx.get("https://localhost:8000", verify="/tmp/client.pem")
>>> r
Response <200 OK>
```

## Supported async environments

HTTPX supports either `asyncio` or `trio` as an async environment.

By default it will auto-detect which of those two to use as the backend
for socket operations and concurrency primitives.

You can also explicitly select a backend by instantiating a client with the
`backend` argument...

```python
client = httpx.AsyncClient(backend='auto')     # Autodetection. The default case.
client = httpx.AsyncClient(backend='asyncio')  # Use asyncio as the backend.
client = httpx.AsyncClient(backend='trio')     # Use trio as the backend.
```

### [AsyncIO](https://docs.python.org/3/library/asyncio.html)

AsyncIO is Python's [built-in library](https://docs.python.org/3/library/asyncio.html)
for writing concurrent code with the async/await syntax.

```python
import asyncio
import httpx

async def main():
    client = httpx.AsyncClient()
    response = await client.get('https://www.example.com/')
    print(response)

asyncio.run(main())
```

### [Trio](https://github.com/python-trio/trio)

Trio is [an alternative async library](https://trio.readthedocs.io/en/stable/),
designed around the [the principles of structured concurrency](https://en.wikipedia.org/wiki/Structured_concurrency).

```python
import httpx
import trio

async def main():
    client = httpx.AsyncClient()
    response = await client.get('https://www.example.com/')
    print(response)

trio.run(main)
```

!!! important
    The `trio` package must be installed to use the Trio backend.
