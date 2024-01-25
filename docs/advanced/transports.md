HTTPX's `Client` also accepts a `transport` argument. This argument allows you
to provide a custom Transport object that will be used to perform the actual
sending of the requests.

## HTTPTransport

For some advanced configuration you might need to instantiate a transport
class directly, and pass it to the client instance. One example is the
`local_address` configuration which is only available via this low-level API.

```pycon
>>> import httpx
>>> transport = httpx.HTTPTransport(local_address="0.0.0.0")
>>> client = httpx.Client(transport=transport)
```

Connection retries are also available via this interface. Requests will be retried the given number of times in case an `httpx.ConnectError` or an `httpx.ConnectTimeout` occurs, allowing smoother operation under flaky networks. If you need other forms of retry behaviors, such as handling read/write errors or reacting to `503 Service Unavailable`, consider general-purpose tools such as [tenacity](https://github.com/jd/tenacity).

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

## WSGI Transport

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

## Mock transports

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

## Mounting transports

The `httpx.Mounts` and `httpx.AsyncMounts` transport classes allow you to map URL patterns to HTTP transports. HTTPX matches requested URLs against URL patterns to decide which transport should be used, if any. Matching is done from most specific URL patterns (e.g. `https://<domain>:<port>`) to least specific ones (e.g. `https://`).

HTTPX supports routing requests based on **scheme**, **domain**, **port**, or a combination of these.

Make sure that you're using `httpx.Mounts` if you're working with `httpx.Client` instance, or `httpx.AsyncMounts` if you're working with `httpx.AsyncClient`.

**Scheme routing**

URL patterns should start with a scheme.

The following example routes HTTP requests through a proxy, and send HTTPS requests directly...

```python
transport = httpx.Mounts({
    "http://": httpx.HTTPTransport(proxy="http://localhost:8030"),
    "https://": httpx.HTTPTransport(),
})
client = httpx.Client(transport=transport)
```

**Domain routing**

The `all://` scheme will match any URL scheme. URL patterns may also include a domain.

Uses cases here might include setting particular SSL or HTTP version configurations for a given domain. For example, disabling HTTP/2 on one particular site...

```python
transport = httpx.Mounts({
    "all://": httpx.HTTPTransport(http2=True),
    "all://*example.org": httpx.HTTPTransport()
})
client = httpx.Client(transport=transport)
```

An alternate use case might be sending all requests on a given domain to a mock application, while allowing all other requests to pass through...

```python
import httpx

def hello_world(request: httpx.Request):
    return httpx.Response("<p>Hello, World!</p>")

transport = httpx.Mounts({
    "all://example.com": httpx.MockTransport(app=hello_world),
    "all://": httpx.HTTPTransport()
})
client = httpx.Client(transport=transport)
```

If we would like to also include subdomains we can use a leading wildcard...

```python
transport = httpx.Mounts({
    "all://*example.com": httpx.MockTransport(app=hello_world),
    "all://": httpx.HTTPTransport()
})
```

Or if we want to only route to *subdomains* of `example.com`, but allow all other requests to pass through...

```python
transport = httpx.Mounts({
    "all://*.example.com": httpx.MockTransport(app=example_subdomains),
    "all://example.com": httpx.MockTransport(app=example),
    "all://": httpx.HTTPTransport(),
})
```

**Port routing**

The URL patterns also support port matching...

```python
transport = httpx.Mounts({
    "all://*:1234": httpx.HTTPTransport(proxy="http://localhost:8030"),
    "all://": httpx.HTTPTransport(),
})
client = httpx.Client(transport=transport)
```

## Custom transports

A transport instance must implement the low-level Transport API which deals
with sending a single request, and returning a response. You should either
subclass `httpx.BaseTransport` to implement a transport to use with `Client`,
or subclass `httpx.AsyncBaseTransport` to implement a transport to
use with `AsyncClient`.

At the layer of the transport API we're using the familiar `Request` and
`Response` models.

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

    def handle_request(self, request):
        return httpx.Response(200, json={"text": "Hello, world!"})
```

Or this example, which uses a custom transport and `httpx.Mounts` to always redirect `http://` requests.

```python
class HTTPSRedirect(httpx.BaseTransport):
    """
    A transport that always redirects to HTTPS.
    """
    def handle_request(self, request):
        url = request.url.copy_with(scheme="https")
        return httpx.Response(303, headers={"Location": str(url)})

# A client where any `http` requests are always redirected to `https`
transport = httpx.Mounts({
    'http://': HTTPSRedirect()
    'https://': httpx.HTTPTransport()
})
client = httpx.Client(transport=transport)
```

A useful pattern here is custom transport classes that wrap the default HTTP implementation. For example...

```python
class DebuggingTransport(httpx.BaseTransport):
    def __init__(self, **kwargs):
        self._wrapper = httpx.HTTPTransport(**kwargs)

    def handle_request(self, request):
        print(f">>> {request}")
        response = self._wrapper.handle_request(request)
        print(f"<<< {response}")
        return response

    def close(self):
        self._wrapper.close()

transport = DebuggingTransport()
client = httpx.Client(transport=transport)
```

Here's another case, where we're using a round-robin across a number of different proxies...

```python
class ProxyRoundRobin(httpx.BaseTransport):
    def __init__(self, proxies, **kwargs):
        self._transports = [
            httpx.HTTPTransport(proxy=proxy, **kwargs)
            for proxy in proxies
        ]
        self._idx = 0

    def handle_request(self, request):
        transport = self._transports[self._idx]
        self._idx = (self._idx + 1) % len(self._transports)
        return transport.handle_request(request)

    def close(self):
        for transport in self._transports:
            transport.close()

proxies = [
    httpx.Proxy("http://127.0.0.1:8081"),
    httpx.Proxy("http://127.0.0.1:8082"),
    httpx.Proxy("http://127.0.0.1:8083"),
]
transport = ProxyRoundRobin(proxies=proxies)
client = httpx.Client(transport=transport)
```