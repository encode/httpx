# Parallel Requests

!!! warning
    This page documents some proposed functionality that is not yet released.
    See [pull request #52](https://github.com/encode/httpx/pull/52) for the
    first-pass of an implementation.

HTTPX allows you to make HTTP requests in parallel in a highly efficient way,
using async under the hood, while still presenting a standard threaded interface.

This has the huge benefit of allowing you to efficiently make parallel HTTP
requests without having to switch out to using async all the way through.

## Making Parallel Requests

Let's make two outgoing HTTP requests in parallel:

```python
>>> with httpx.parallel() as parallel:
>>>     pending_one = parallel.get('https://example.com/1')
>>>     pending_two = parallel.get('https://example.com/2')
>>>     response_one = pending_one.get_response()
>>>     response_two = pending_two.get_response()
```

If we're making lots of outgoing requests, we might not want to deal with the
responses sequentially, but rather deal with each response that comes back
as soon as it's available:

```python
>>> with httpx.parallel() as parallel:
>>>     for counter in range(1, 10):
>>>         parallel.get(f'https://example.com/{counter}')
>>>     while parallel.has_pending_responses:
>>>         r = parallel.next_response()
```

## Exceptions and Cancellations

The style of using `parallel` blocks ensures that you'll always have a well-defined exception and cancellation behaviors. Request exceptions are only ever
raised when calling either `get_response` or `next_response` and any pending
requests are canceled on exiting the block.

## Parallel requests with a Client

You can also call `parallel()` from a client instance, which allows you to
control the authentication or dispatch behavior for all requests within the
block.

```python
>>> with httpx.Client() as client:
...     with client.parallel() as parallel:
...         ...
```

## Async parallel requests

If you're working within an async framework, then you'll want to use a fully
async API for making requests.

```python
>>> async with httpx.AsyncClient() as client:
...     async with client.parallel() as parallel:
...         pending_one = await parallel.get('https://example.com/1')
...         pending_two = await parallel.get('https://example.com/2')
...         response_one = await pending_one.get_response()
...         response_two = await pending_two.get_response()
```

See [the Async Client documentation](async.md) for more details.
