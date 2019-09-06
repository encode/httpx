# Advanced Usage

## Client Instances

Using a Client instance to make requests will give you HTTP connection pooling,
will provide cookie persistence, and allows you to apply configuration across
all outgoing requests.

```python
>>> client = httpx.Client()
>>> r = client.get('https://example.org/')
>>> r
<Response [200 OK]>
```

## Calling into Python Web Apps

You can configure an `httpx` client to call directly into a Python web
application, using either the WSGI or ASGI protocol.

This is particularly useful for two main use-cases:

* Using `httpx` as a client, inside test cases.
* Mocking out external services, during tests or in dev/staging environments.

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

* Inspect 500 error responses, rather than raise exceptions, by setting `raise_app_exceptions=False`.
* Mount the WSGI or ASGI application at a subpath, by setting `script_name` (WSGI) or `root_path` (ASGI).
* Use a given the client address for requests, by setting `remote_addr` (WSGI) or `client` (ASGI).

For example:

```python
# Instantiate a client that makes WSGI requests with a client IP of "1.2.3.4".
dispatch = httpx.WSGIDispatch(app=app, remote_addr="1.2.3.4")
client = httpx.Client(dispatch=dispatch)
```

## Build Request

You can use `Client.build_request()` to build a request and
make modifications before sending the request.

```python
>>> client = httpx.Client()
>>> r = client.build_request("OPTIONS", "https://example.com")
>>> req.url.full_path = "*"  # Build an 'OPTIONS *' request for CORS
>>> client.send(r)
<Response [200 OK]>
```

## .netrc Support

HTTPX supports .netrc file. In `trust_env=True` cases, if auth parameter is
not defined, HTTPX tries to add auth into request's header from .netrc file.

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
