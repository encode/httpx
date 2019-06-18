# Advanced Usage

## Client Instances

Using a Client instance to make requests will give you HTTP connection pooling,
will provide cookie persistence, and allows you to apply configuration across
all outgoing requests.

```python
>>> client = http3.Client()
>>> r = client.get('https://example.org/')
>>> r
<Response [200 OK]>
```

## Calling into Python Web Apps

You can configure an `http3` client to call directly into a Python web
application, using either the WSGI or ASGI protocol.

This is particularly useful for two main use-cases:

* Using `http3` as a client, inside test cases.
* Mocking out external services, during tests or in dev/staging environments.

Here's an example of integrating against a Flask application:

```python
from flask import Flask
import http3


app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

client = http3.Client(app=app)
r = client.get('http://example/')
assert r.status_code == 200
assert r.text == "Hello World!"
```
