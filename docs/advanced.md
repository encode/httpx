# Advanced Usage

## Client Instances

!!! hint
    If you are coming from Requests, `httpx.Client()` is what you can use instead of `requests.Session()`.

### Why use a Client?

!!! note "TL;DR"
    If you do anything more than experimentation, one-off scripts, or prototypes, then you should use a `Client` instance.

#### More efficient usage of network resources

When you make requests using the top-level API as documented in the [Quickstart](quickstart.md) guide, HTTPX has to establish a new connection _for every single request_ (connections are not reused). As the number of requests to a host increases, this quickly becomes inefficient.

On the other hand, a `Client` instance uses [HTTP connection pooling](https://en.wikipedia.org/wiki/HTTP_persistent_connection). This means that when you make several requests to the same host, the `Client` will reuse the underlying TCP connection, instead of recreating one for every single request.

This can bring **significant performance improvements** compared to using the top-level API, including:

- Reduced latency across requests (no handshaking).
- Reduced CPU usage and round-trips.
- Reduced network congestion.

#### Extra features

`Client` instances also support features that aren't available at the top-level API, such as:

- Cookie persistance across requests.
- Applying configuration across all outgoing requests.
- Sending requests through HTTP proxies.
- Using [HTTP/2](http2.md).

The other sections on this page go into further detail about what you can do with a `Client` instance.

### Usage

The recommended way to use a `Client` is as a context manager. This will ensure that connections are properly cleaned up when leaving the `with` block:

```python
with httpx.Client() as client:
    ...
```

Alternatively, you can explicitly close the connection pool without block-usage using `.close()`:

```python
client = httpx.Client()
try:
    ...
finally:
    client.close()
```

### Making requests

Once you have a `Client`, you can send requests using `.get()`, `.post()`, etc. For example:

```pycon
>>> with httpx.Client() as client:
...     r = client.get('https://example.com')
...
>>> r
<Response [200 OK]>
```

These methods accept the same arguments as `httpx.get()`, `httpx.post()`, etc. This means that all features documented in the [Quickstart](quickstart.md) guide are also available at the client level.

For example, to send a request with custom headers:

```pycon
>>> with httpx.Client() as client:
...     headers = {'X-Custom': 'value'}
...     r = client.get('https://example.com', headers=headers)
...
>>> r.request.headers['X-Custom']
'value'
```

### Sharing configuration across requests

Clients allow you to apply configuration to all outgoing requests by passing parameters to the `Client` constructor.

For example, to apply a set of custom headers _on every request_:

```pycon
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> with httpx.Client(headers=headers) as client:
...     r = client.get(url)
...
>>> r.json()['headers']['User-Agent']
'my-app/0.0.1'
```

### Merging of configuration

When a configuration option is provided at both the client-level and request-level, one of two things can happen:

- For headers, query parameters and cookies, the values are combined together. For example:

```pycon
>>> headers = {'X-Auth': 'from-client'}
>>> params = {'client_id': 'client1'}
>>> with httpx.Client(headers=headers, params=params) as client:
...     headers = {'X-Custom': 'from-request'}
...     params = {'request_id': 'request1'}
...     r = client.get('https://example.com', headers=headers, params=params)
...
>>> r.request.url
URL('https://example.com?client_id=client1&request_id=request1')
>>> r.request.headers['X-Auth']
'from-client'
>>> r.request.headers['X-Custom']
'from-request'
```

- For all other parameters, the request-level value takes priority. For example:

```pycon
>>> with httpx.Client(auth=('tom', 'mot123')) as client:
...     r = client.get('https://example.com', auth=('alice', 'ecila123'))
...
>>> _, _, auth = r.request.headers['Authorization'].partition(' ')
>>> import base64
>>> base64.b64decode(auth)
b'alice:ecila123'
```

If you need finer-grained control on the merging of client-level and request-level parameters, see [Request instances](#request-instances).

### Other Client-only configuration options

Additionally, `Client` accepts some configuration options that aren't available at the request level.

For example, `base_url` allows you to prepend an URL to all outgoing requests:

```pycon
>>> with httpx.Client(base_url='http://httpbin.org') as client:
...     r = client.get('/headers')
...
>>> r.request.url
URL('http://httpbin.org/headers')
```

For a list of all available client parameters, see the [`Client`](api.md#client) API reference.

## Calling into Python Web Apps

You can configure an `httpx` client to call directly into a Python web application using the WSGI protocol.

This is particularly useful for two main use-cases:

* Using `httpx` as a client inside test cases.
* Mocking out external services during tests or in dev/staging environments.

Here's an example of integrating against a Flask application:

```python
from flask import Flask
import httpx


app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

with httpx.Client(app=app, base_url="http://testserver") as client:
    r = client.get("/")
    assert r.status_code == 200
    assert r.text == "Hello World!"
```

For some more complex cases you might need to customize the WSGI transport. This allows you to:

* Inspect 500 error responses rather than raise exceptions by setting `raise_app_exceptions=False`.
* Mount the WSGI application at a subpath by setting `script_name` (WSGI).
* Use a given client address for requests by setting `remote_addr` (WSGI).

For example:

```python
# Instantiate a client that makes WSGI requests with a client IP of "1.2.3.4".
transport = httpx.WSGITransport(app=app, remote_addr="1.2.3.4")
with httpx.Client(transport=transport, base_url="http://testserver") as client:
    ...
```

## Request instances

For maximum control on what gets sent over the wire, HTTPX supports building explicit [`Request`](api.md#request) instances:

```python
request = httpx.Request("GET", "https://example.com")
```

To dispatch a `Request` instance across to the network, create a [`Client` instance](#client-instances) and use `.send()`:

```python
with httpx.Client() as client:
    response = client.send(request)
    ...
```

If you need to mix client-level and request-level options in a way that is not supported by the default [Merging of parameters](#merging-of-parameters), you can use `.build_request()` and then make arbitrary modifications to the `Request` instance. For example:

```python
headers = {"X-Api-Key": "...", "X-Client-ID": "ABC123"}

with httpx.Client(headers=headers) as client:
    request = client.build_request("GET", "https://api.example.com")

    print(request.headers["X-Client-ID"])  # "ABC123"

    # Don't send the API key for this particular request.
    del request.headers["X-Api-Key"]

    response = client.send(request)
    ...
```

## Event Hooks

HTTPX allows you to register "event hooks" with the client, that are called
every time a particular type of event takes place.

There are currently two event hooks:

* `request` - Called after a request is fully prepared, but before it is sent to the network. Passed the `request` instance.
* `response` - Called after the response has been fetched from the network, but before it is returned to the caller. Passed the `response` instance.

These allow you to install client-wide functionality such as logging, monitoring or tracing.

```python
def log_request(request):
    print(f"Request event hook: {request.method} {request.url} - Waiting for response")

def log_response(response):
    request = response.request
    print(f"Response event hook: {request.method} {request.url} - Status {response.status_code}")

client = httpx.Client(event_hooks={'request': [log_request], 'response': [log_response]})
```

You can also use these hooks to install response processing code, such as this
example, which creates a client instance that always raises `httpx.HTTPStatusError`
on 4xx and 5xx responses.

```python
def raise_on_4xx_5xx(response):
    response.raise_for_status()

client = httpx.Client(event_hooks={'response': [raise_on_4xx_5xx]})
```

The hooks are also allowed to modify `request` and `response` objects.

```python
def add_timestamp(request):
    request.headers['x-request-timestamp'] = datetime.now(tz=datetime.utc).isoformat()
    
client = httpx.Client(event_hooks={'request': [add_timestamp]})
```

Event hooks must always be set as a **list of callables**, and you may register
multiple event hooks for each type of event.

As well as being able to set event hooks on instantiating the client, there
is also an `.event_hooks` property, that allows you to inspect and modify
the installed hooks.

```python
client = httpx.Client()
client.event_hooks['request'] = [log_request]
client.event_hooks['response'] = [log_response, raise_on_4xx_5xx]
```

!!! note
    If you are using HTTPX's async support, then you need to be aware that
    hooks registered with `httpx.AsyncClient` MUST be async functions,
    rather than plain functions.

## Monitoring download progress

If you need to monitor download progress of large responses, you can use response streaming and inspect the `response.num_bytes_downloaded` property.

This interface is required for properly determining download progress, because the total number of bytes returned by `response.content` or `response.iter_content()` will not always correspond with the raw content length of the response if HTTP response compression is being used.

For example, showing a progress bar using the [`tqdm`](https://github.com/tqdm/tqdm) library while a response is being downloaded could be done like this…

```python
import tempfile

import httpx
from tqdm import tqdm

with tempfile.NamedTemporaryFile() as download_file:
    url = "https://speed.hetzner.de/100MB.bin"
    with httpx.stream("GET", url) as response:
        total = int(response.headers["Content-Length"])

        with tqdm(total=total, unit_scale=True, unit_divisor=1024, unit="B") as progress:
            num_bytes_downloaded = response.num_bytes_downloaded
            for chunk in response.iter_bytes():
                download_file.write(chunk)
                progress.update(response.num_bytes_downloaded - num_bytes_downloaded)
                num_bytes_downloaded = response.num_bytes_downloaded
```

![tqdm progress bar](img/tqdm-progress.gif)

Or an alternate example, this time using the [`rich`](https://github.com/willmcgugan/rich) library…

```python
import tempfile
import httpx
import rich.progress

with tempfile.NamedTemporaryFile() as download_file:
    url = "https://speed.hetzner.de/100MB.bin"
    with httpx.stream("GET", url) as response:
        total = int(response.headers["Content-Length"])

        with rich.progress.Progress(
            "[progress.percentage]{task.percentage:>3.0f}%",
            rich.progress.BarColumn(bar_width=None),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
        ) as progress:
            download_task = progress.add_task("Download", total=total)
            for chunk in response.iter_bytes():
                download_file.write(chunk)
                progress.update(download_task, completed=response.num_bytes_downloaded)
```

![rich progress bar](img/rich-progress.gif)

## .netrc Support

HTTPX supports .netrc file. In `trust_env=True` cases, if auth parameter is
not defined, HTTPX tries to add auth into request's header from .netrc file.

!!! note
    The NETRC file is cached across requests made by a client.
    If you need to refresh the cache (e.g. because the NETRC file has changed),
    you should create a new client or restart the interpreter.

As default `trust_env` is true. To set false:
```pycon
>>> httpx.get('https://example.org/', trust_env=False)
```

If `NETRC` environment is empty, HTTPX tries to use default files.
(`~/.netrc`, `~/_netrc`)

To change `NETRC` environment:
```pycon
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

When using `Client` instances, `trust_env` should be set on the client itself, rather than on the request methods:

```python
client = httpx.Client(trust_env=False)
```

## HTTP Proxying

HTTPX supports setting up [HTTP proxies](https://en.wikipedia.org/wiki/Proxy_server#Web_proxy_servers) via the `proxies` parameter to be passed on client initialization or top-level API functions like `httpx.get(..., proxies=...)`.

_Note: SOCKS proxies are not supported yet._

<div align="center">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Open_proxy_h2g2bob.svg/480px-Open_proxy_h2g2bob.svg.png"/>
    <figcaption><em>Diagram of how a proxy works (source: Wikipedia). The left hand side "Internet" blob may be your HTTPX client requesting <code>example.com</code> through a proxy.</em></figcaption>
</div>

### Example

To route all traffic (HTTP and HTTPS) to a proxy located at `http://localhost:8030`, pass the proxy URL to the client...

```python
with httpx.Client(proxies="http://localhost:8030") as client:
    ...
```

For more advanced use cases, pass a proxies `dict`. For example, to route HTTP and HTTPS requests to 2 different proxies, respectively located at `http://localhost:8030`, and `http://localhost:8031`, pass a `dict` of proxy URLs:

```python
proxies = {
    "http://": "http://localhost:8030",
    "https://": "http://localhost:8031",
}

with httpx.Client(proxies=proxies) as client:
    ...
```

For detailed information about proxy routing, see the [Routing](#routing) section.

!!! tip "Gotcha"
    In most cases, the proxy URL for the `https://` key _should_ use the `http://` scheme (that's not a typo!).

    This is because HTTP proxying requires initiating a connection with the proxy server. While it's possible that your proxy supports doing it via HTTPS, most proxies only support doing it via HTTP.

    For more information, see [FORWARD vs TUNNEL](#forward-vs-tunnel).

### Authentication

Proxy credentials can be passed as the `userinfo` section of the proxy URL. For example:

```python
proxies = {
    "http://": "http://username:password@localhost:8030",
    # ...
}
```

### Routing

HTTPX provides fine-grained controls for deciding which requests should go through a proxy, and which shouldn't. This process is known as proxy routing.

The `proxies` dictionary maps URL patterns ("proxy keys") to proxy URLs. HTTPX matches requested URLs against proxy keys to decide which proxy should be used, if any. Matching is done from most specific proxy keys (e.g. `https://<domain>:<port>`) to least specific ones (e.g. `https://`).

HTTPX supports routing proxies based on **scheme**, **domain**, **port**, or a combination of these.

#### Wildcard routing

Route everything through a proxy...

```python
proxies = {
    "all://": "http://localhost:8030",
}
```

#### Scheme routing

Route HTTP requests through one proxy, and HTTPS requests through another...

```python
proxies = {
    "http://": "http://localhost:8030",
    "https://": "http://localhost:8031",
}
```

#### Domain routing

Proxy all requests on domain "example.com", let other requests pass through...

```python
proxies = {
    "all://example.com": "http://localhost:8030",
}
```

Proxy HTTP requests on domain "example.com", let HTTPS and other requests pass through...

```python
proxies = {
    "http://example.com": "http://localhost:8030",
}
```

Proxy all requests to "example.com" and its subdomains, let other requests pass through...

```python
proxies = {
    "all://*example.com": "http://localhost:8030",
}
```

Proxy all requests to strict subdomains of "example.com", let "example.com" and other requests pass through...

```python
proxies = {
    "all://*.example.com": "http://localhost:8030",
}
```

#### Port routing

Proxy HTTPS requests on port 1234 to "example.com"...

```python
proxies = {
    "https://example.com:1234": "http://localhost:8030",
}
```

Proxy all requests on port 1234...

```python
proxies = {
    "all://*:1234": "http://localhost:8030",
}
```

#### No-proxy support

It is also possible to define requests that _shouldn't_ be routed through proxies.

To do so, pass `None` as the proxy URL. For example...

```python
proxies = {
    # Route requests through a proxy by default...
    "all://": "http://localhost:8031",
    # Except those for "example.com".
    "all://example.com": None,
}
```

#### Complex configuration example

You can combine the routing features outlined above to build complex proxy routing configurations. For example...

```python
proxies = {
    # Route all traffic through a proxy by default...
    "all://": "http://localhost:8030",
    # But don't use proxies for HTTPS requests to "domain.io"...
    "https://domain.io": None,
    # And use another proxy for requests to "example.com" and its subdomains...
    "all://*example.com": "http://localhost:8031",
    # And yet another proxy if HTTP is used,
    # and the "internal" subdomain on port 5550 is requested...
    "http://internal.example.com:5550": "http://localhost:8032",
}
```

#### Environment variables

HTTP proxying can also be configured through environment variables, although with less fine-grained control.

See documentation on [`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`](environment_variables.md#http_proxy-https_proxy-all_proxy) for more information.

### Proxy mechanisms

!!! note
    This section describes **advanced** proxy concepts and functionality.

#### FORWARD vs TUNNEL

In general, the flow for making an HTTP request through a proxy is as follows:

1. The client connects to the proxy (initial connection request).
1. The proxy somehow transfers data to the server on your behalf.

How exactly step 2/ is performed depends on which of two proxying mechanisms is used:

* **Forwarding**: the proxy makes the request for you, and sends back the response it obtained from the server.
* **Tunneling**: the proxy establishes a TCP connection to the server on your behalf, and the client reuses this connection to send the request and receive the response. This is known as an [HTTP Tunnel](https://en.wikipedia.org/wiki/HTTP_tunnel). This mechanism is how you can access websites that use HTTPS from an HTTP proxy (the client "upgrades" the connection to HTTPS by performing the TLS handshake with the server over the TCP connection provided by the proxy).

#### Default behavior

Given the technical definitions above, by default (and regardless of whether you're using an HTTP or HTTPS proxy), HTTPX will:

* Use forwarding for HTTP requests.
* Use tunneling for HTTPS requests.

This ensures that you can make HTTP and HTTPS requests in all cases (i.e. regardless of which type of proxy you're using).

#### Forcing the proxy mechanism

In most cases, the default behavior should work just fine as well as provide enough security.

But if you know what you're doing and you want to force which mechanism to use, you can do so by passing an `httpx.Proxy()` instance, setting the `mode` to either `FORWARD_ONLY` or `TUNNEL_ONLY`. For example...

```python
# Route all requests through an HTTPS proxy, using tunneling only.
proxies = httpx.Proxy(
    url="https://localhost:8030",
    mode="TUNNEL_ONLY",
)

with httpx.Client(proxies=proxies) as client:
    # This HTTP request will be tunneled instead of forwarded.
    r = client.get("http://example.com")
```

### Troubleshooting proxies

If you encounter issues when setting up proxies, please refer to our [Troubleshooting guide](troubleshooting.md#proxies).

## Timeout Configuration

HTTPX is careful to enforce timeouts everywhere by default.

The default behavior is to raise a `TimeoutException` after 5 seconds of
network inactivity.

### Setting and disabling timeouts

You can set timeouts for an individual request:

```python
# Using the top-level API:
httpx.get('http://example.com/api/v1/example', timeout=10.0)

# Using a client instance:
with httpx.Client() as client:
    client.get("http://example.com/api/v1/example", timeout=10.0)
```

Or disable timeouts for an individual request:

```python
# Using the top-level API:
httpx.get('http://example.com/api/v1/example', timeout=None)

# Using a client instance:
with httpx.Client() as client:
    client.get("http://example.com/api/v1/example", timeout=None)
```

### Setting a default timeout on a client

You can set a timeout on a client instance, which results in the given
`timeout` being used as the default for requests made with this client:

```python
client = httpx.Client()              # Use a default 5s timeout everywhere.
client = httpx.Client(timeout=10.0)  # Use a default 10s timeout everywhere.
client = httpx.Client(timeout=None)  # Disable all timeouts by default.
```

### Fine tuning the configuration

HTTPX also allows you to specify the timeout behavior in more fine grained detail.

There are four different types of timeouts that may occur. These are **connect**,
**read**, **write**, and **pool** timeouts.

* The **connect** timeout specifies the maximum amount of time to wait until
a socket connection to the requested host is established. If HTTPX is unable to connect
within this time frame, a `ConnectTimeout` exception is raised.
* The **read** timeout specifies the maximum duration to wait for a chunk of
data to be received (for example, a chunk of the response body). If HTTPX is
unable to receive data within this time frame, a `ReadTimeout` exception is raised.
* The **write** timeout specifies the maximum duration to wait for a chunk of
data to be sent (for example, a chunk of the request body). If HTTPX is unable
to send data within this time frame, a `WriteTimeout` exception is raised.
* The **pool** timeout specifies the maximum duration to wait for acquiring
a connection from the connection pool. If HTTPX is unable to acquire a connection
within this time frame, a `PoolTimeout` exception is raised. A related
configuration here is the maximum number of allowable connections in the
connection pool, which is configured by the `limits` argument.

You can configure the timeout behavior for any of these values...

```python
# A client with a 60s timeout for connecting, and a 10s timeout elsewhere.
timeout = httpx.Timeout(10.0, connect=60.0)
client = httpx.Client(timeout=timeout)

response = client.get('http://example.com/')
```

## Pool limit configuration

You can control the connection pool size using the `limits` keyword
argument on the client. It takes instances of `httpx.Limits` which define:

- `max_keepalive`, number of allowable keep-alive connections, or `None` to always
allow. (Defaults 20)
- `max_connections`, maximum number of allowable connections, or` None` for no limits.
(Default 100)

```python
limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
client = httpx.Client(limits=limits)
```

## Multipart file encoding

As mentioned in the [quickstart](quickstart.md#sending-multipart-file-uploads)
multipart file encoding is available by passing a dictionary with the
name of the payloads as keys and either tuple of elements or a file-like object or a string as values.

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

```pycon
>>> files = {'upload-file': (None, 'text content', 'text/plain')}
>>> r = httpx.post("https://httpbin.org/post", files=files)
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

!!! tip
    It is safe to upload large files this way. File uploads are streaming by default, meaning that only one chunk will be loaded into memory at a time.

 Non-file data fields can be included in the multipart form using by passing them to `data=...`.

You can also send multiple files in one go with a multiple file field form.
To do that, pass a list of `(field, <file>)` items instead of a dictionary, allowing you to pass multiple items with the same `field`.
For instance this request sends 2 files, `foo.png` and `bar.png` in one request on the `images` form field:

```pycon
>>> files = [('images', ('foo.png', open('foo.png', 'rb'), 'image/png')),
                      ('images', ('bar.png', open('bar.png', 'rb'), 'image/png'))]
>>> r = httpx.post("https://httpbin.org/post", files=files)
```

## Customizing authentication

When issuing requests or instantiating a client, the `auth` argument can be used to pass an authentication scheme to use. The `auth` argument may be one of the following...

* A two-tuple of `username`/`password`, to be used with basic authentication.
* An instance of `httpx.BasicAuth()` or `httpx.DigestAuth()`.
* A callable, accepting a request and returning an authenticated request instance.
* A subclass of `httpx.Auth`.

The most involved of these is the last, which allows you to create authentication flows involving one or more requests. A subclass of `httpx.Auth` should implement `def auth_flow(request)`, and yield any requests that need to be made...

```python
class MyCustomAuth(httpx.Auth):
    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
        # Send the request, with a custom `X-Authentication` header.
        request.headers['X-Authentication'] = self.token
        yield request
```

If the auth flow requires more that one request, you can issue multiple yields, and obtain the response in each case...

```python
class MyCustomAuth(httpx.Auth):
    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
      response = yield request
      if response.status_code == 401:
          # If the server issues a 401 response then resend the request,
          # with a custom `X-Authentication` header.
          request.headers['X-Authentication'] = self.token
          yield request
```

Custom authentication classes are designed to not perform any I/O, so that they may be used with both sync and async client instances. If you are implementing an authentication scheme that requires the request body, then you need to indicate this on the class using a `requires_request_body` property.

You will then be able to access `request.content` inside the `.auth_flow()` method.

```python
class MyCustomAuth(httpx.Auth):
    requires_request_body = True

    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
      response = yield request
      if response.status_code == 401:
          # If the server issues a 401 response then resend the request,
          # with a custom `X-Authentication` header.
          request.headers['X-Authentication'] = self.sign_request(...)
          yield request

    def sign_request(self, request):
        # Create a request signature, based on `request.method`, `request.url`,
        # `request.headers`, and `request.content`.
        ...
```

Similarly, if you are implementing a scheme that requires access to the response body, then use the `requires_response_body` property.   You will then be able to access response body properties and methods such as `response.content`, `response.text`, `response.json()`, etc.

```python
class MyCustomAuth(httpx.Auth):
    requires_response_body = True

    def __init__(self, access_token, refresh_token, refresh_url):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_url = refresh_url

    def auth_flow(self, request):
        request.headers["X-Authentication"] = self.access_token
        response = yield request

        if response.status_code == 401:
            # If the server issues a 401 response, then issue a request to
            # refresh tokens, and resend the request.
            refresh_response = yield self.build_refresh_request()
            self.update_tokens(refresh_response)

            request.headers["X-Authentication"] = self.access_token
            yield request

    def build_refresh_request(self):
        # Return an `httpx.Request` for refreshing tokens.
        ...

    def update_tokens(self, response):
        # Update the `.access_token` and `.refresh_token` tokens
        # based on a refresh response.
        data = response.json()
        ...
```

If you _do_ need to perform I/O other than HTTP requests, such as accessing a disk-based cache, or you need to use concurrency primitives, such as locks, then you should override `.sync_auth_flow()` and `.async_auth_flow()` (instead of `.auth_flow()`). The former will be used by `httpx.Client`, while the latter will be used by `httpx.AsyncClient`.

```python
import asyncio
import threading
import httpx


class MyCustomAuth(httpx.Auth):
    def __init__(self):
        self._sync_lock = threading.RLock()
        self._async_lock = asyncio.Lock()

    def sync_get_token(self):
        with self._sync_lock:
            ...

    def sync_auth_flow(self, request):
        token = self.sync_get_token()
        request.headers["Authorization"] = f"Token {token}"
        yield request

    async def async_get_token(self):
        async with self._async_lock:
            ...

    async def async_auth_flow(self, request):
        token = await self.async_get_token()
        request.headers["Authorization"] = f"Token {token}"
        yield request
```

If you only want to support one of the two methods, then you should still override it, but raise an explicit `RuntimeError`.

```python
import httpx
import sync_only_library


class MyCustomAuth(httpx.Auth):
    def sync_auth_flow(self, request):
        token = sync_only_library.get_token(...)
        request.headers["Authorization"] = f"Token {token}"
        yield request

    async def async_auth_flow(self, request):
        raise RuntimeError("Cannot use a sync authentication class with httpx.AsyncClient")
```

## SSL certificates

When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

### Changing the verification defaults

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/). This is what you want in most cases, even though some advanced situations may require you to use a different set of certificates.

If you'd like to use a custom CA bundle, you can use the `verify` parameter.

```python
import httpx

r = httpx.get("https://example.org", verify="path/to/client.pem")
```

Alternatively, you can pass a standard library `ssl.SSLContext`.

```pycon
>>> import ssl
>>> import httpx
>>> context = ssl.create_default_context()
>>> context.load_verify_locations(cafile="/tmp/client.pem")
>>> httpx.get('https://example.org', verify=context)
<Response [200 OK]>
```

We also include a helper function for creating properly configured `SSLContext` instances.

```pycon
>>> context = httpx.create_ssl_context()
```

The `create_ssl_context` function accepts the same set of SSL configuration arguments
(`trust_env`, `verify`, `cert` and `http2` arguments)
as `httpx.Client` or `httpx.AsyncClient`

```pycon
>>> import httpx
>>> context = httpx.create_ssl_context(verify="/tmp/client.pem")
>>> httpx.get('https://example.org', verify=context)
<Response [200 OK]>
```

Or you can also disable the SSL verification entirely, which is _not_ recommended.

```python
import httpx

r = httpx.get("https://example.org", verify=False)
```

### SSL configuration on client instances

If you're using a `Client()` instance, then you should pass any SSL settings when instantiating the client.

```python
client = httpx.Client(verify=False)
```

The `client.get(...)` method and other request methods *do not* support changing the SSL settings on a per-request basis. If you need different SSL settings in different cases you should use more that one client instance, with different settings on each. Each client will then be using an isolated connection pool with a specific fixed SSL configuration on all connections within that pool.

### Client Side Certificates

You can also specify a local cert to use as a client-side certificate, either a path to an SSL certificate file, or two-tuple of (certificate file, key file), or a three-tuple of (certificate file, key file, password)

```python
import httpx

r = httpx.get("https://example.org", cert="path/to/client.pem")
```

Alternatively,

```pycon
>>> cert = ("path/to/client.pem", "path/to/client.key")
>>> httpx.get("https://example.org", cert=cert)
<Response [200 OK]>
```

or

```pycon
>>> cert = ("path/to/client.pem", "path/to/client.key", "password")
>>> httpx.get("https://example.org", cert=cert)
<Response [200 OK]>
```

### Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme-cli](https://github.com/sethmlarson/trustme-cli/) to generate a pair of server key/cert files, and a client cert file.
1. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
1. Tell HTTPX to use the certificates stored in `client.pem`:

```pycon
>>> import httpx
>>> r = httpx.get("https://localhost:8000", verify="/tmp/client.pem")
>>> r
Response <200 OK>
```

## Custom Transports

HTTPX's `Client` also accepts a `transport` argument. This argument allows you
to provide a custom Transport object that will be used to perform the actual
sending of the requests.

### Usage

For some advanced configuration you might need to instantiate a transport
class directly, and pass it to the client instance. One example is the
`local_address` configuration which is only available via this low-level API.

```pycon
>>> import httpx
>>> transport = httpx.HTTPTransport(local_address="0.0.0.0")
>>> client = httpx.Client(transport=transport)
```

Connection retries are also available via this interface.

```pycon
>>> import httpx
>>> transport = httpx.HTTPTransport(retries=1)
>>> client = httpx.Client(transport=transport)
```

Similarly, instantiating a transport directly provides a `uds` option for
connecting via a Unix Domain Socket that is only available via this low-level API:

```pycon
>>> import httpx
>>> # Connect to the Docker API via a Unix Socket.
>>> transport = httpx.HTTPTransport(uds="/var/run/docker.sock")
>>> client = httpx.Client(transport=transport)
>>> response = client.get("http://docker/info")
>>> response.json()
{"ID": "...", "Containers": 4, "Images": 74, ...}
```

### urllib3 transport

This [public gist](https://gist.github.com/florimondmanca/d56764d78d748eb9f73165da388e546e) provides a transport that uses the excellent [`urllib3` library](https://urllib3.readthedocs.io/en/latest/), and can be used with the sync `Client`...

```pycon
>>> import httpx
>>> from urllib3_transport import URLLib3Transport
>>> client = httpx.Client(transport=URLLib3Transport())
>>> client.get("https://example.org")
<Response [200 OK]>
```

### Writing custom transports

A transport instance must implement the low-level Transport API, which deals
with sending a single request, and returning a response. You should either
subclass `httpx.BaseTransport` to implement a transport to use with `Client`,
or subclass `httpx.AsyncBaseTransport` to implement a transport to
use with `AsyncClient`.

At the layer of the transport API we're using plain primitives.
No `Request` or `Response` models, no fancy `URL` or `Header` handling.
This strict point of cut-off provides a clear design separation between the
HTTPX API, and the low-level network handling.

See the `handle_request` and `handle_async_request` docstrings for more details
on the specifics of the Transport API.

A complete example of a custom transport implementation would be:

```python
import json
import httpx


class HelloWorldTransport(httpx.BaseTransport):
    """
    A mock transport that always returns a JSON "Hello, world!" response.
    """

    def handle_request(self, method, url, headers, stream, extensions):
        message = {"text": "Hello, world!"}
        content = json.dumps(message).encode("utf-8")
        stream = httpx.ByteStream(content)
        headers = [(b"content-type", b"application/json")]
        extensions = {}
        return 200, headers, stream, extensions
```

Which we can use in the same way:

```pycon
>>> import httpx
>>> client = httpx.Client(transport=HelloWorldTransport())
>>> response = client.get("https://example.org/")
>>> response.json()
{"text": "Hello, world!"}
```

### Mock transports

During testing it can often be useful to be able to mock out a transport,
and return pre-determined responses, rather than making actual network requests.

The `httpx.MockTransport` class accepts a handler function, which can be used
to map requests onto pre-determined responses:

```python
def handler(request):
    return httpx.Response(200, json={"text": "Hello, world!"})


# Switch to a mock transport, if the TESTING environment variable is set.
if os.environ.get('TESTING', '').upper() == "TRUE":
    transport = httpx.MockTransport(handler)
else:
    transport = httpx.HTTPTransport()

client = httpx.Client(transport=transport)
```

For more advanced use-cases you might want to take a look at either [the third-party
mocking library, RESPX](https://lundberg.github.io/respx/), or the [pytest-httpx library](https://github.com/Colin-b/pytest_httpx).

### Mounting transports

You can also mount transports against given schemes or domains, to control
which transport an outgoing request should be routed via, with [the same style
used for specifying proxy routing](#routing).

```python
import httpx

class HTTPSRedirectTransport(httpx.BaseTransport):
    """
    A transport that always redirects to HTTPS.
    """

    def handle_request(self, method, url, headers, stream, extensions):
        scheme, host, port, path = url
        if port is None:
            location = b"https://%s%s" % (host, path)
        else:
            location = b"https://%s:%d%s" % (host, port, path)
        stream = httpx.ByteStream(b"")
        headers = [(b"location", location)]
        extensions = {}
        return 303, headers, stream, extensions


# A client where any `http` requests are always redirected to `https`
mounts = {'http://': HTTPSRedirectTransport()}
client = httpx.Client(mounts=mounts)
```

A couple of other sketches of how you might take advantage of mounted transports...

Disabling HTTP/2 on a single given domain...

```python
mounts = {
    "all://": httpx.HTTPTransport(http2=True),
    "all://*example.org": httpx.HTTPTransport()
}
client = httpx.Client(mounts=mounts)
```

Mocking requests to a given domain:

```python
# All requests to "example.org" should be mocked out.
# Other requests occur as usual.
def handler(request):
    return httpx.Response(200, json={"text": "Hello, World!"})

mounts = {"all://example.org": httpx.MockTransport(handler)}
client = httpx.Client(mounts=mounts)
```

Adding support for custom schemes:

```python
# Support URLs like "file:///Users/sylvia_green/websites/new_client/index.html"
mounts = {"file://": FileSystemTransport()}
client = httpx.Client(mounts=mounts)
```
