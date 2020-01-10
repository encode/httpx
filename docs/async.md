# Async Support

HTTPX offers a standard synchronous API by default, but also gives you
the option of an async client if you need it.

Async is a concurrency model that is far more efficient than multi-threading,
and can provide significant performance benefits and enable the use of
long-lived network connections such as WebSockets.

If you're working with an async web framework then you'll also want to use an
async client for sending outgoing HTTP requests.

## Making Async requests

To make asynchronous requests, you'll need an `AsyncClient`.

```python
>>> async with httpx.AsyncClient() as client:
>>>     r = await client.get('https://www.example.com/')
>>> r
<Response [200 OK]>
```

!!! tip
    Use [IPython](https://ipython.readthedocs.io/en/stable/) or Python 3.8+ with `python -m asyncio` to try this code interactively, as they support executing `async`/`await` expressions in the console.

## API Differences

If you're using an async client then there are a few bits of API that
use async methods.

### Making requests

The request methods are all async, so you should use `response = await client.get(...)` style for all of the following:

* `AsyncClient.get(url, ...)`
* `AsyncClient.options(url, ...)`
* `AsyncClient.head(url, ...)`
* `AsyncClient.post(url, ...)`
* `AsyncClient.put(url, ...)`
* `AsyncClient.patch(url, ...)`
* `AsyncClient.delete(url, ...)`
* `AsyncClient.request(method, url, ...)`
* `AsyncClient.send(request, ...)`

### Opening and closing clients

Use `async with httpx.AsyncClient()` if you want a context-managed client...

```python
async with httpx.AsyncClient() as client:
    ...
```

Alternatively, use `await client.aclose()` if you want to close a client explicitly:

```python
client = httpx.AsyncClient()
...
await client.aclose()
```

### Streaming responses

The `AsyncClient.stream(method, url, ...)` method is an async context block.

```python
>>> client = httpx.AsyncClient()
>>> async with client.stream('GET', 'https://www.example.com/') as response:
>>>     async for chunk in response.aiter_bytes():
>>>         ...
```

The async response streaming methods are:

* `Response.aread()` - For conditionally reading a response inside a stream block.
* `Response.aiter_bytes()` - For streaming the response content as bytes.
* `Response.aiter_text()` - For streaming the response content as text.
* `Response.aiter_lines()` - For streaming the response content as lines of text.
* `Response.aiter_raw()` - For streaming the raw response bytes, without applying content decoding.
* `Response.aclose()` - For closing the response. You don't usually need this, since `.stream` block close the response automatically on exit.

### Streaming requests

When sending a streaming request body with an `AsyncClient` instance, you should use an async bytes generator instead of a bytes generator:

```python
async def upload_bytes():
    ...  # yield byte content

await client.post(url, data=upload_bytes())
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
        response = await client.get('https://www.example.com/')
        print(response)

trio.run(main)
```

!!! important
    The `trio` package must be installed to use the Trio backend.

## Calling into Python Web Apps

Just as `httpx.Client` allows you to call directly into WSGI web applications,
the `httpx.AsyncClient` class allows you to call directly into ASGI web applications.

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
...     r = await client.get('http://example/')
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
dispatch = httpx.ASGIDispatch(app=app, client=("1.2.3.4", 123))
async with httpx.AsyncClient(dispatch=dispatch) as client:
    ...
```

See [the ASGI documentation](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope) for more details on the `client` and `root_path` keys.

## Unix Domain Sockets

The async client provides support for connecting through a unix domain socket via the `uds` parameter. This is useful when making requests to a server that is bound to a socket file rather than an IP address.

Here's an example requesting the Docker Engine API:

```python
import httpx


async with httpx.AsyncClient(uds="/var/run/docker.sock") as client:
    # This request will connect through the socket file.
    resp = await client.get("http://localhost/version")
```

This functionality is not currently available in the synchronous client.
