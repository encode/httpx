# The ASGI transport

You can configure an `httpx` client to call directly into an async Python web application using the ASGI protocol.

This is particularly useful for two main use-cases:

* Using `httpx` as a client inside test cases.
* Mocking out external services during tests or in dev or staging environments.

## Using `ASGITransport`

Let's take this Starlette application as an example:

```python
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route


async def hello(request):
    return HTMLResponse("Hello World!")


app = Starlette(routes=[Route("/", hello)])
```

We can make requests directly against the application, like so:

```python
transport = httpx.ASGITransport(app=app)

async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
    r = await client.get("/")
    assert r.status_code == 200
    assert r.text == "Hello World!"
```

## Configuration options

For some more complex cases you might need to customise the ASGI transport. This allows you to:

* Inspect 500 error responses rather than raise exceptions by setting `raise_app_exceptions=False`.
* Mount the ASGI application at a subpath by setting `root_path`.
* Use a given client address for requests by setting `client`.

For example:

```python
# Instantiate a client that makes ASGI requests with a client IP of "1.2.3.4",
# on port 123.
transport = httpx.ASGITransport(app=app, client=("1.2.3.4", 123))
async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
    ...
```

See [the ASGI documentation](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope) for more details on the `client` and `root_path` keys.

## ASGI startup and shutdown

It is not in the scope of HTTPX to trigger lifespan events of your app.

However it is suggested to use `LifespanManager` from [asgi-lifespan](https://github.com/florimondmanca/asgi-lifespan#usage) in pair with `AsyncClient`.