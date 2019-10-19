# Advanced Usage

## Client Instances

Using a Client instance to make requests will give you HTTP connection pooling,
will provide cookie persistence, and allows you to apply configuration across
all outgoing requests.

A Client instance is equivalent to a Session instance in `requests`.

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

client = httpx.Client(app=app)
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
client = httpx.Client(dispatch=dispatch)
```

## Build Request

You can use `Client.build_request()` to build a request and
make modifications before sending the request.

```python
>>> client = httpx.Client()
>>> req = client.build_request("OPTIONS", "https://example.com")
>>> req.url.full_path = "*"  # Build an 'OPTIONS *' request for CORS
>>> client.send(r)
<Response [200 OK]>
```

## Specify the version of the HTTP protocol

One can set the version of the HTTP protocol for the client in case you want to make the requests using a specific version.

For example:

```python
h11_client = httpx.Client(http_versions=["HTTP/1.1"])
h11_response = h11_client.get("https://myserver.com")

h2_client = httpx.Client(http_versions=["HTTP/2"])
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
>>> client = httpx.Client(proxies={
  "http": "http://127.0.0.1:3080",
  "https": "http://127.0.0.1:3081"
})
```

Proxies can be configured for a specific scheme and host, all schemes of a host,
all hosts for a scheme, or for all requests. When determining which proxy configuration
to use for a given request this same order is used.

```python
>>> client = httpx.Client(proxies={
    "http://example.com":  "...",  # Host+Scheme
    "all://example.com":  "...",  # Host
    "http": "...",  # Scheme
    "all": "...",  # All
})
>>> client = httpx.Client(proxies="...")  # Shortcut for 'all'
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
client = httpx.Client(proxies=proxy)

# This request will be tunneled instead of forwarded.
client.get("http://example.com")
```


## Timeout fine-tuning
HTTPX offers various request timeout management options. Three types of timeouts are available: **connect** timeouts, 
**write** timeouts and **read** timeouts.

* The **connect timeout** specifies the maximum amount of time to wait until a connection to the requested host is established.   
If HTTPX is unable to connect within this time frame, a `ConnectTimeout` exception is raised.
* The **write timeout** specifies the maximum duration to wait for a chunk of data to be sent (for example, a chunk of the request body).   
If HTTPX is unable to send data within this time frame, a `WriteTimeout` exception is raised.
* The **read timeout** specifies the maximum duration to wait for a chunk of data to be received (for example, a chunk of the response body).  
If HTTPX is unable to receive data within this time frame, a `ReadTimeout` exception is raised.

### Setting timeouts
You can set timeouts on two levels:

- For a given request:

```python
# Using top-level API
httpx.get('http://example.com/api/v1/example', timeout=5)

# Or, with a client:
client = httpx.Client()
client.get("http://example.com/api/v1/example", timeout=5)
```

- On a client instance, which results in the given `timeout` being used as a default for requests made with this client:

```python
client = httpx.Client(timeout=5)
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
By default all types of timeouts are set to 5 second.
 
### Disabling timeouts
To disable timeouts, you can pass `None` as a timeout parameter.  
Note that currently this is not supported by the top-level API.

```python
url = "http://example.com/api/v1/delay/10"

httpx.get(url, timeout=None)  # Times out after 5s


client = httpx.Client(timeout=None)
client.get(url)  # Does not timeout, returns after 10s


timeout = httpx.TimeoutConfig(
    connect_timeout=5, 
    read_timeout=None, 
    write_timeout=5
)
httpx.get(url, timeout=timeout) # Does not timeout, returns after 10s
```
