# Advanced Usage

## Client Instances

Using a Client instance to make requests will give you HTTP connection pooling,
will provide cookie persistence, and allows you to apply configuration across
all outgoing requests.

!!! hint
    A Client instance is equivalent to a Session instance in `requests`.

### Usage

The recommended way to use a `Client` is as a context manager. This will ensure that connections are properly cleaned up when leaving the `with` block:

```python
>>> with httpx.Client() as client:
...     r = client.get('https://example.com')
... 
>>> r
<Response [200 OK]>
```

Alternatively, you can explicitly close the connection pool without block-usage using `.close()`:

```python
>>> client = httpx.Client()
>>> try:
...     r = client.get('https://example.com')
... finally:
...     client.close()
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
>>> with httpx.Client(headers=headers) as client:
...     r = client.get(url)
...
>>> r.json()['headers']['User-Agent']
'my-app/0.0.1'
```

!!! note
    When you provide a parameter at both the client and request levels, one of two things can happen:
    
    - For headers, query parameters and cookies, the values are merged into one.
    - For all other parameters, the request-level value is used.

Additionally, `Client` constructor accepts some parameters that aren't available at the request level.

One particularly useful parameter is `base_url`, which allows you to define a base URL to prepend to all outgoing requests:

```python
>>> with httpx.Client(base_url='http://httpbin.org') as client:
...     r = client.get('/headers')
... 
>>> r.request.url
URL('http://httpbin.org/headers')
```

For a list of all available client-level parameters, see the [`Client` API reference](/api/#client).

## Calling into Python Web Apps

You can configure an `httpx` client to call directly into a Python web
application using either the WSGI or ASGI protocol.

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

with httpx.Client(app=app) as client:
    r = client.get('http://example/')
    assert r.status_code == 200
    assert r.text == "Hello World!"
```

For some more complex cases you might need to customize the WSGI or ASGI
dispatch. This allows you to:

* Inspect 500 error responses rather than raise exceptions by setting `raise_app_exceptions=False`.
* Mount the WSGI or ASGI application at a subpath by setting `script_name` (WSGI) or `root_path` (ASGI).
* Use a given client address for requests by setting `remote_addr` (WSGI) or `client` (ASGI).

For example:

```python
# Instantiate a client that makes WSGI requests with a client IP of "1.2.3.4".
dispatch = httpx.dispatch.WSGIDispatch(app=app, remote_addr="1.2.3.4")
with httpx.Client(dispatch=dispatch) as client:
    ...
```

## Build Request

You can use `Client.build_request()` to build a request and
make modifications before sending the request.

```python
>>> with httpx.Client() as client:
...     req = client.build_request("OPTIONS", "https://example.com")
...     req.url.full_path = "*"  # Build an 'OPTIONS *' request for CORS
...     r = client.send(req)
...
>>> r
<Response [200 OK]>
```

## Specify the version of the HTTP protocol

One can set the version of the HTTP protocol for the client in case you want to make the requests using a specific version.

For example:

```python
with httpx.Client(http_versions=["HTTP/1.1"]) as h11_client:
    h11_response = h11_client.get("https://myserver.com")

with httpx.Client(http_versions=["HTTP/2"]) as h2_client:
    h2_response = h2_client.get("https://myserver.com")
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
>>> httpx.get('https://example.org/', trust_env=False)
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

## HTTP Proxying

HTTPX supports setting up proxies the same way that Requests does via the `proxies` parameter.
For example to forward all HTTP traffic to `http://127.0.0.1:3080` and all HTTPS traffic
to `http://127.0.0.1:3081` your `proxies` config would look like this:

```python
>>> proxies = {
...     "http": "http://127.0.0.1:3080",
...     "https": "http://127.0.0.1:3081"
... }
>>> with httpx.Client(proxies=proxies) as client:
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
>>> with httpx.Client(proxies=proxies) as client:
...     ...
... 
>>> proxy = "..."  # Shortcut for {'all': '...'}
>>> with httpx.Client(proxies=proxy) as client:
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
    proxy_mode=httpx.HTTPProxyMode.TUNNEL_ONLY
)
with httpx.Client(proxies=proxy) as client:
    # This request will be tunneled instead of forwarded.
    r = client.get("http://example.com")
```

!!! note

    Per request proxy configuration, i.e. `client.get(url, proxies=...)`,
    has not been implemented yet. To use proxies you must pass the proxy
    information at `Client` initialization.

## Timeout fine-tuning

HTTPX offers various request timeout management options. Three types of timeouts
are available: **connect** timeouts, **write** timeouts and **read** timeouts.

* The **connect timeout** specifies the maximum amount of time to wait until
a connection to the requested host is established. If HTTPX is unable to connect
within this time frame, a `ConnectTimeout` exception is raised.
* The **write timeout** specifies the maximum duration to wait for a chunk of
data to be sent (for example, a chunk of the request body). If HTTPX is unable
to send data within this time frame, a `WriteTimeout` exception is raised.
* The **read timeout** specifies the maximum duration to wait for a chunk of
data to be received (for example, a chunk of the response body). If HTTPX is
unable to receive data within this time frame, a `ReadTimeout` exception is raised.

### Setting timeouts

You can set timeouts on two levels:

- For a given request:

```python
# Using top-level API
httpx.get('http://example.com/api/v1/example', timeout=5)

# Or, with a client:
with httpx.Client() as client:
    client.get("http://example.com/api/v1/example", timeout=5)
```

- On a client instance, which results in the given `timeout` being used as a default for requests made with this client:

```python
with httpx.Client(timeout=5) as client:
    client.get('http://example.com/api/v1/example')
```

Besides, you can pass timeouts in two forms:

- A number, which sets the read, write and connect timeouts to the same value, as in the examples above.
- A `TimeoutConfig` instance, which allows to define the read, write and connect timeouts independently:

```python
timeout = httpx.TimeoutConfig(
    connect_timeout=5,
    read_timeout=10,
    write_timeout=15
)

resp = httpx.get('http://example.com/api/v1/example', timeout=timeout)
```

### Default timeouts

By default all types of timeouts are set to 5 seconds.

Default timeouts are applied whenever you don't specify a timeout, or you pass `None` as a timeout value.

For example, all the following calls will timeout because default timeouts are applied:

```python
url = "https://httpbin.org/delay/10"

# No timeout given.
httpx.get(url)

# Using 'None' does not disable timeouts -- see note below.
httpx.get(url, timeout=None)

# 'TimeoutConfig()' returns the default timeout configuration.
httpx.get(url, timeout=httpx.TimeoutConfig())

# Again, passing 'None' as a timeout value does disable timeouts.
httpx.get(url, timeout=httpx.TimeoutConfig(read_timeout=None))

# 'read_timeout' is not given, so the default value is used.
httpx.get(url, timeout=httpx.TimeoutConfig(connect_timeout=3))
```

!!! question
    The fact that using `timeout=None` results in HTTPX still applying default timeouts may be surprising to you. Indeed, this differs from what most HTTP libraries do. HTTPX does this so that disabling timeouts (as documented in the next section) is always a very explicit decision.

### Disabling timeouts

To disable timeouts, you must pass `False` as a timeout parameter.

For example, none of these calls will time out:

```python
url = "https://httpbin.org/delay/10"

# Timeouts are disabled for this request.
httpx.get(url, timeout=False)

# Timeouts are disabled for all requests made with this client.
with httpx.Client(timeout=False) as client:
    client.get(url)

with httpx.Client() as client:
    # Timeouts are disabled for this request only.
    client.get(url, timeout=False)

# Only read timeout is disabled for this request.
timeout = httpx.TimeoutConfig(read_timeout=False)
httpx.get(url, timeout=timeout)
```

## Multipart file encoding

As mentioned in the [quickstart](/quickstart#sending-multipart-file-uploads)
multipart file encoding is available by passing a dictionary with the
name of the payloads as keys and a tuple of elements as values.

```python
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

More specifically, this tuple must have at least two elements and maximum of three:
- The first one is an optional file name which can be set to `None`.
- The second may be a file-like object or a string which will be automatically
encoded in UTF-8.
- An optional third element can be included with the
[MIME type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_Types)
of the file being uploaded. If not specified HTTPX will attempt to guess the MIME type
based on the file name specified as the first element or the tuple, if that
is set to `None` or it cannot be inferred from it, HTTPX will default to
`applicaction/octet-stream`.

```python
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
