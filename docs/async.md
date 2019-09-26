# Async Client

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
    Use [IPython](https://ipython.readthedocs.io/en/stable/) to try this code interactively, as it supports executing `async`/`await` expressions in the console.

!!! note
    The `async with` syntax ensures that all active connections are closed on exit.

    It is safe to access response content (e.g. `r.text`) both inside and outside the `async with` block, unless you are using response streaming. In that case, you should `.read()`, `.stream()`, or `.close()` the response *inside* the `async with` block.

## API Differences

If you're using streaming responses then there are a few bits of API that
use async methods:

```python
>>> async with httpx.AsyncClient() as client:
>>>     r = await client.get('https://www.example.com/', stream=True)
>>>     async for chunk in r.stream():
>>>         ...
```

The async response methods are:

* `.read()`
* `.stream()`
* `.raw()`
* `.close()`

If you're making [parallel requests](/parallel/), then you'll also need to use an async API:

```python
>>> async with httpx.AsyncClient() as client:
>>>     async with client.parallel() as parallel:
>>>         pending_one = parallel.get('https://example.com/1')
>>>         pending_two = parallel.get('https://example.com/2')
>>>         response_one = await pending_one.get_response()
>>>         response_two = await pending_two.get_response()
```

The async parallel methods are:

* `.parallel()` *Used as an "async with" context manager.*
* `.get_response()`
* `.next_response()`

## Supported async libraries

You can use `AsyncClient` with any of the following async libraries.

!!! tip
    You will typically be using `AsyncClient` in async programs that run on `asyncio`. If that's the case, or if you're not sure what this is all about, you can safely ignore this section.

### [asyncio](https://docs.python.org/3/library/asyncio.html) (Default)

By default, `AsyncClient` uses `asyncio` to perform asynchronous operations and I/O calls.

```python
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        ...

asyncio.run(main())
```

### [trio](https://github.com/python-trio/trio)

To make asynchronous requests in `trio` programs, pass a `TrioBackend` to the `AsyncClient`:

```python
import trio
import httpx
from httpx.concurrency.trio import TrioBackend

async def main():
    async with httpx.AsyncClient(backend=TrioBackend()) as client:
        ...

trio.run(main)
```

!!! important
    `trio` must be installed to import and use the `TrioBackend`.
