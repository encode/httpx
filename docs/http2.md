# HTTP/2

HTTP/2 is a major new iteration of the HTTP protocol, that provides a far more
efficient transport, with potential performance benefits. HTTP/2 does not change
the core semantics of the request or response, but alters the way that data is
sent to and from the server.

Rather that the text format that HTTP/1.1 uses, HTTP/2 is a binary format.
The binary format provides full request and response multiplexing, and efficient
compression of HTTP headers. The stream multiplexing means that where HTTP/1.1
requires one TCP stream for each concurrent request, HTTP/2 allows a single TCP
stream to handle multiple concurrent requests.

HTTP/2 also provides support for functionality such as response prioritization,
and server push.

## Enabling HTTP/2

The HTTPX client provides provisional HTTP/2 support.

The HTTP/2 support is not enabled by default, because HTTP/1.1 a mature,
battle-hardened transport layer. With HTTP/2 being newer and significantly more
complex, it should be considered a less robust option at this point in time.

However, if you're issuing highly concurrent requests you might want to consider
trying out our HTTP/2 support. You can do so by instantiating a client with
HTTP/2 support enabled.

Simply instantiating a client...

```python
client = httpx.Client(http_2=True)
...
```

Instantiating a client as a context manager, to ensure that all connections
are nicely closed at the end of it's usage...

```python
async with httpx.Client(http_2=True) as client:
    ...
```
