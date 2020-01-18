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

Additionally, `Client` accepts some parameters that aren't available at the request level.

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

with httpx.Client(app=app) as client:
    r = client.get('http://example/')
    assert r.status_code == 200
    assert r.text == "Hello World!"
```

For some more complex cases you might need to customize the WSGI dispatch. This allows you to:

* Inspect 500 error responses rather than raise exceptions by setting `raise_app_exceptions=False`.
* Mount the WSGI application at a subpath by setting `script_name` (WSGI).
* Use a given client address for requests by setting `remote_addr` (WSGI).

For example:

```python
# Instantiate a client that makes WSGI requests with a client IP of "1.2.3.4".
dispatch = httpx.WSGIDispatch(app=app, remote_addr="1.2.3.4")
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

When using `Client` instances, `trust_env` should be set on the client itself, rather that on the request methods:

```python
client = httpx.Client(trust_env=False)
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

By default `httpx.Proxy` will operate as a forwarding proxy for `http://...` requests
and will establish a `CONNECT` TCP tunnel for `https://` requests. This doesn't change
regardless of the proxy `url` being `http` or `https`.

Proxies can be configured to have different behavior such as forwarding or tunneling all requests:

```python
proxy = httpx.Proxy(
    url="https://127.0.0.1",
    mode="TUNNEL_ONLY"  # May be "TUNNEL_ONLY" or "FORWARD_ONLY". Defaults to "DEFAULT".
)
with httpx.Client(proxies=proxy) as client:
    # This request will be tunneled instead of forwarded.
    r = client.get("http://example.com")
```

!!! note

    To use proxies you must pass the proxy information at `Client` initialization,
    rather than on the `.get(...)` call or other request methods.

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
client = httpx.Client(timeout=timeout)

response = client.get('http://example.com/')
```

## Multipart file encoding

As mentioned in the [quickstart](/quickstart#sending-multipart-file-uploads)
multipart file encoding is available by passing a dictionary with the
name of the payloads as keys and either tuple of elements or a file-like object or a string as values.

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

## SSL certificates

When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

### Changing the verification defaults

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/). This is what you want in most cases, even though some advanced situations may require you to use a different set of certificates.

If you'd like to use a custom CA bundle, you can use the `verify` parameter.

```python
import httpx

r = httpx.get("https://example.org", verify="path/to/client.pem")
```

You can also disable the SSL verification...

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

### Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme-cli](https://github.com/sethmlarson/trustme-cli/) to generate a pair of server key/cert files, and a client cert file.
1. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
1. Tell HTTPX to use the certificates stored in `client.pem`:

```python
>>> import httpx
>>> r = httpx.get("https://localhost:8000", verify="/tmp/client.pem")
>>> r
Response <200 OK>
```

## Retries

Communicating with a peer over a network is by essence subject to errors. HTTPX provides built-in retry functionality to increase the resilience to unexpected issues such as network faults or connection issues.

The default behavior is to retry at most 3 times on connection and network errors before marking the request as failed and bubbling up any exceptions. The delay between retries is increased each time to prevent overloading the requested server.

### Setting and disabling retries

You can set the retry behavior on a client instance, which results in the given behavior being used for all requests made with this client:

```python
client = httpx.Client()           # Retry at most 3 times on connection failures.
client = httpx.Client(retries=5)  # Retry at most 5 times on connection failures.
client = httpx.Client(retries=0)  # Disable retries.
```

### Fine-tuning the retries configuration

When instantiating a client, the `retries` argument may be one of the following...

* An integer, representing the maximum number connection failures to retry on. Use `0` to disable retries entirely.

```python
client = httpx.Client(retries=5)
```

* An `httpx.Retries()` instance. It accepts the number of connection failures to retry on as a positional argument. The `backoff_factor` keyword argument that specifies how fast the time to wait before issuing a retry request should be increased. By default this is `0.2`, which corresponds to issuing a new request after `(0s, 0.2s, 0.4s, 0.8s, ...)`. (Note that a lot of errors are immediately resolved after retrying, so HTTPX will always issue the initial retry right away.)

```python
# Retry at most 5 times on connection failures,
# and issue new requests after `(0s, 0.5s, 1s, 2s, 4s, ...)`
retries = httpx.Retries(5, backoff_factor=0.5)
client = httpx.Client(retries=retries)
```

### Advanced retries customization

The first argument to `httpx.Retries()` can also be a subclass of `httpx.RetryLimits`. This is useful if you want to replace or extend the default behavior of retrying on connection failures.

The `httpx.RetryLimits` subclass should implement the `.retry_flow()` method, `yield` any request to be made, and prepare for the following situations...

* (A) The request resulted in an `httpx.HTTPError`. If it shouldn't be retried on, `raise` the error as-is. If it should be retried on, you should make any necessary modifications to the request, and continue yielding. If you've exceeded a maximum number of retries, wrap the error in `httpx.TooManyRetries()`, and raise the result.
* (B) The request went through and resulted in the client sending back a `response`. If it shouldn't be retried on, `return` to terminate the retry flow. If it should be retried on (e.g. because it is an error response), you should make any necessary modifications to the request, and continue yielding. If you've exceeded a maximum number of retries, wrap the response in `httpx.TooManyRetries()`, and raise the result.

As an example, here's how you could implement a custom retry limiting policy that retries on certain status codes:

```python
import httpx

class RetryOnStatusCodes(httpx.RetryLimits):
    def __init__(self, limit, status_codes):
        self.limit = limit
        self.status_codes = status_codes

    def retry_flow(self, request):
        retries_left = self.limit

        while True:
            response = yield request

            if response.status_code not in self.status_codes:
                return

            if retries_left == 0:
                try:
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise httpx.TooManyRetries(exc, response=response)
                else:
                    raise httpx.TooManyRetries(response=response)

            retries_left -= 1
```

To use a custom policy:

* Explicitly pass the number of times to retry on connection failures as a first positional argument to `httpx.Retries()`. (Use `0` to not retry on these failures.)
* Pass the custom policy as a second positional argument.

For example...

```python
# Retry at most 3 times on connection failures, and at most three times
# on '429 Too Many Requests', '502 Bad Gateway', or '503 Service Unavailable'.
retries = httpx.Retries(3, RetryOnStatusCodes(3, status_codes={429, 502, 503}))
```
