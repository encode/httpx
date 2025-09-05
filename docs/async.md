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
    Use [IPython](https://ipython.readthedocs.io/en/stable/) or Python 3.9+ with `python -m asyncio` to try this code interactively, as they support executing `async`/`await` expressions in the console.

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

!!! warning
    In order to get the most benefit from connection pooling, make sure you're not instantiating multiple client instances - for example by using `async with` inside a "hot loop". This can be achieved either by having a single scoped client that's passed throughout wherever it's needed, or by having a single global client instance.

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

For situations when context block usage is not practical, it is possible to enter "manual mode" by sending a [`Request` instance](advanced/clients.md#request-instances) using `client.send(..., stream=True)`.

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

await client.post(url, content=upload_bytes())
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

## Calling into Python Web Apps

For details on calling directly into ASGI applications, see [the `ASGITransport` docs](../advanced/transports#asgitransport).