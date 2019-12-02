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

For a comprehensive guide to HTTP/2 you may want to check out "[HTTP2 Explained](https://http2-explained.haxx.se/content/en/)".

## Enabling HTTP/2

The HTTPX client provides provisional HTTP/2 support.

HTTP/2 support is not enabled by default, because HTTP/1.1 is a mature,
battle-hardened transport layer. With HTTP/2 being newer and significantly more
complex, our implementation should be considered a less robust option at this
point in time.

However, if you're issuing highly concurrent requests you might want to consider
trying out our HTTP/2 support. You can do so by instantiating a client with
HTTP/2 support enabled:

```python
client = httpx.Client(http_2=True)
...
```

You can also instantiate a client as a context manager, to ensure that all
HTTP connections are nicely scoped, and will be closed once the context block
is exited.

```python
async with httpx.Client(http_2=True) as client:
    ...
```

## Inspecting the HTTP version

Enabling HTTP/2 support on the client does not *necessarily* mean that your
requests and responses will be transported over HTTP/2, since both the client
*and* the server need to support HTTP/2. If you connect to a server that only
supports HTTP/1.1 the client will use a standard HTTP/1.1 connection instead.

You can determine which version of the HTTP protocol was used by examining
the `.http_version` property on the response.

```python
client = httpx.Client(http_2=True)
response = await client.get(...)
print(response.http_version)  # "HTTP/1.0", "HTTP/1.1", or "HTTP/2".
```
