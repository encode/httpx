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

```pycon
>>> async with httpx.AsyncClient() as client:
...     r = await client.get('https://www.example.com/')
...
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

```pycon
>>> client = httpx.AsyncClient()
>>> async with client.stream('GET', 'https://www.example.com/') as response:
...     async for chunk in response.aiter_bytes():
...         ...
```

The async response streaming methods are:

* `Response.aread()` - For conditionally reading a response inside a stream block.
* `Response.aiter_bytes()` - For streaming the response content as bytes.
* `Response.aiter_text()` - For streaming the response content as text.
* `Response.aiter_lines()` - For streaming the response content as lines of text.
* `Response.aiter_raw()` - For streaming the raw response bytes, without applying content decoding.
* `Response.aclose()` - For closing the response. You don't usually need this, since `.stream` block closes the response automatically on exit.

For situations when context block usage is not practical, it is possible to enter "manual mode" by sending a [`Request` instance](./advanced.md#request-instances) using `client.send(..., stream=True)`.

Example in the context of forwarding the response to a streaming web endpoint with [Starlette](https://www.starlette.io):

```python
import httpx
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

client = httpx.AsyncClient()

async def home(request):
    req = client.build_request("GET", "https://www.example.com/")
    r = await client.send(req, stream=True)
    return StreamingResponse(r.aiter_text(), background=BackgroundTask(r.aclose))
```

!!! warning
    When using this "manual streaming mode", it is your duty as a developer to make sure that `Response.aclose()` is called eventually. Failing to do so would leave connections open, most likely resulting in resource leaks down the line.

### Streaming requests

When sending a streaming request body with an `AsyncClient` instance, you should use an async bytes generator instead of a bytes generator:

```python
async def upload_bytes():
    ...  # yield byte content

await client.post(url, data=upload_bytes())
```

### Explicit transport instances

When instantiating a transport instance directly, you need to use `httpx.AsyncHTTPTransport`.

For instance:

```pycon
>>> import httpx
>>> transport = httpx.AsyncHTTPTransport(retries=1)
>>> async with httpx.AsyncClient(transport=transport) as client:
>>>     ...
```

## Supported async environments

HTTPX supports either `asyncio` or `trio` as an async environment.

It will auto-detect which of those two to use as the backend
for socket operations and concurrency primitives.

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


### [Curio](https://github.com/dabeaz/curio)

Curio is a [coroutine-based library](https://curio.readthedocs.io/en/latest/tutorial.html)
for concurrent Python systems programming.

```python
import httpx
import curio

async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://www.example.com/')
        print(response)

curio.run(main)
```

!!! important
    The `curio` package must be installed to use the Curio backend.


### [AnyIO](https://github.com/agronholm/anyio)

AnyIO is an [asynchronous networking and concurrency library](https://anyio.readthedocs.io/) that works on top of either `asyncio` or `trio`. It blends in with native libraries of your chosen backend (defaults to `asyncio`).

```python
import httpx
import anyio

async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://www.example.com/')
        print(response)

anyio.run(main, backend='trio')
```

When instantiating a transport instance explicitly, for maximum consistency, the same `backend` parameter can be passed to `AsyncHTTPTransport`.
```python
transport = httpx.AsyncHTTPTransport(backend="trio")
```


## Calling into Python Web Apps

Just as `httpx.Client` allows you to call directly into WSGI web applications,
the `httpx.AsyncClient` class allows you to call directly into ASGI web applications.

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

```pycon
>>> import httpx
>>> async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
...     r = await client.get("/")
...     assert r.status_code == 200
...     assert r.text == "Hello World!"
```

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

## Startup/shutdown of ASGI apps

It is not in the scope of HTTPX to trigger lifespan events of your app.

However it is suggested to use `LifespanManager` from [asgi-lifespan](https://github.com/florimondmanca/asgi-lifespan#usage) in pair with `AsyncClient`.
