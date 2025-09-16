# Network Backends

The lowest level network abstractions in `httpx` are the `NetworkBackend` and `NetworkStream` classes. These provide a consistent interface onto the operations for working with a network stream, typically over a TCP connection. Different runtimes (threaded, trio & asyncio) are supported via alternative implementations of the core interface.

---

## `NetworkBackend()`

The default backend is instantiated via the `NetworkBackend` class...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> net = httpx.NetworkBackend()
>>> net
<NetworkBackend [threaded]>
```

```{ .python .ahttpx .hidden }
>>> net = ahttpx.NetworkBackend()
>>> net
<NetworkBackend [asyncio]>
```

### `.connect(host, port)`

A TCP stream is created using the `connect` method...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> net = httpx.NetworkBackend()
>>> stream = net.connect("www.encode.io", 80)
>>> stream
<NetworkStream ["168.0.0.1:80"]>
```

```{ .python .ahttpx .hidden }
>>> net = ahttpx.NetworkBackend()
>>> stream = await net.connect("www.encode.io", 80)
>>> stream
<NetworkStream ["168.0.0.1:80"]>
```

Streams support being used in a context managed style. The cleanest approach to resource management is to use `.connect(...)` in the context of a `with` block.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> net = httpx.NetworkBackend()
>>> with net.connect("dev.encode.io", 80) as stream:
>>>     ...
>>> stream
<NetworkStream ["168.0.0.1:80" CLOSED]>
```

```{ .python .ahttpx .hidden }
>>> net = ahttpx.NetworkBackend()
>>> async with await net.connect("dev.encode.io", 80) as stream:
>>>     ...
>>> stream
<NetworkStream ["168.0.0.1:80" CLOSED]>
```

## `NetworkStream(sock)`

The `NetworkStream` class provides TCP stream abstraction, by providing a thin wrapper around a socket instance.

Network streams do not provide any built-in thread or task locking.
Within `httpx` thread and task saftey is handled at the `Connection` layer.

### `.read(max_bytes=None)`

Read up to `max_bytes` bytes of data from the network stream.
If no limit is provided a default value of 64KB will be used.

### `.write(data)`

Write the given bytes of `data` to the network stream.

### `.start_tls(ctx, hostname)`

Upgrade a stream to TLS (SSL) connection for sending secure `https://` requests.

`<NetworkStream [“168.0.0.1:443” TLS]>`

### `.get_extra_info(key)`

Return information about the underlying resource. May include...

* `"client_addr"` - Return the client IP and port.
* `"server_addr"` - Return the server IP and port.
* `"ssl_object"` - Return an `ssl.SSLObject` instance.
* `"socket"` - Access the raw socket instance.

### `.close()`

Close the network stream. For TLS streams this will attempt to send a closing handshake before terminating the conmection.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> net = httpx.NetworkBackend()
>>> stream = net.connect("dev.encode.io", 80)
>>> try:
>>>     ...
>>> finally:
>>>     stream.close()
>>> stream
<NetworkStream ["168.0.0.1:80" CLOSED]>
```

```{ .python .ahttpx .hidden }
>>> net = ahttpx.NetworkBackend()
>>> stream = await net.connect("dev.encode.io", 80)
>>> try:
>>>     ...
>>> finally:
>>>     await stream.close()
>>> stream
<NetworkStream ["168.0.0.1:80" CLOSED]>
```

---

## Timeouts

Network timeouts are handled using a context block API.

This [design approach](https://vorpus.org/blog/timeouts-and-cancellation-for-humans) avoids timeouts needing to passed around throughout the stack, and provides an obvious and natural API to dealing with timeout contexts.

### timeout(duration)

The timeout context manager can be used to wrap socket operations anywhere in the stack.

Here's an example of enforcing an overall 3 second timeout on a request.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.Client() as cli:
>>>     with httpx.timeout(3.0):
>>>         res = cli.get('https://www.example.com')
>>>         print(res)
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.Client() as cli:
>>>     async with ahttpx.timeout(3.0):
>>>         res = await cli.get('https://www.example.com')
>>>         print(res)
```

Timeout contexts provide an API allowing for deadlines to be cancelled.

### .cancel()

In this example we enforce a 3 second timeout on *receiving the start of* a streaming HTTP response...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> with httpx.Client() as cli:
>>>     with httpx.timeout(3.0) as t:
>>>         with cli.stream('https://www.example.com') as r:
>>>             t.cancel()
>>>             print(">>>", res)
>>>             for chunk in r.stream:
>>>                 print("...", chunk)
```

```{ .python .ahttpx .hidden }
>>> async with ahttpx.Client() as cli:
>>>     async with ahttpx.timeout(3.0) as t:
>>>         async with await cli.stream('https://www.example.com') as r:
>>>             t.cancel()
>>>             print(">>>", res)
>>>             async for chunk in r.stream:
>>>                 print("...", chunk)
```

---

## Sending HTTP requests

Let's take a look at how we can work directly with a network backend to send an HTTP request, and recieve an HTTP response.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
import httpx
import ssl
import truststore

net = httpx.NetworkBackend()
ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
req = b'\r\n'.join([
    b'GET / HTTP/1.1',
    b'Host: www.example.com',
    b'User-Agent: python/dev',
    b'Connection: close',
    b'',
    b'',
])

# Use a 10 second overall timeout for the entire request/response.
with httpx.timeout(10.0):
    # Use a 3 second timeout for the initial connection.
    with httpx.timeout(3.0) as t:
        # Open the connection & establish SSL.
        with net.connect("www.example.com", 443) as stream:
            stream.start_tls(ctx, hostname="www.example.com")
            t.cancel()
            # Send the request & read the response.
            stream.write(req)
            buffer = []
            while part := stream.read():
                buffer.append(part)
            resp = b''.join(buffer)
```

```{ .python .ahttpx .hidden }
import ahttpx
import ssl
import truststore

net = ahttpx.NetworkBackend()
ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
req = b'\r\n'.join([
    b'GET / HTTP/1.1',
    b'Host: www.example.com',
    b'User-Agent: python/dev',
    b'Connection: close',
    b'',
    b'',
])

# Use a 10 second overall timeout for the entire request/response.
async with ahttpx.timeout(10.0):
    # Use a 3 second timeout for the initial connection.
    async with ahttpx.timeout(3.0) as t:
        # Open the connection & establish SSL.
        async with await net.connect("www.example.com", 443) as stream:
            await stream.start_tls(ctx, hostname="www.example.com")
            t.cancel()
            # Send the request & read the response.
            await stream.write(req)
            buffer = []
            while part := await stream.read():
                buffer.append(part)
            resp = b''.join(buffer)
```

The example above is somewhat contrived, there's no HTTP parsing implemented so we can't actually determine when the response is complete. We're using a `Connection: close` header to request that the server close the connection once the response is complete.

A more complete example would require proper HTTP parsing. The `Connection` class implements an HTTP request/response interface, layered over a `NetworkStream`.

---

## Custom network backends

The interface for implementing custom network backends is provided by two classes...

### `NetworkBackendInterface`

The abstract interface implemented by `NetworkBackend`. See above for details.

### `NetworkStreamInterface`

The abstract interface implemented by `NetworkStream`. See above for details.

### An example backend

We can use these interfaces to implement custom functionality. For example, here we're providing a network backend that logs all the ingoing and outgoing bytes.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
class RecordingBackend(httpx.NetworkBackendInterface):
    def __init__(self):
        self._backend = NetworkBackend()

    def connect(self, host, port):
        # Delegate creating connections to the default
        # network backend, and return a wrapped stream.
        stream = self._backend.connect(host, port)
        return RecordingStream(stream)


class RecordingStream(httpx.NetworkStreamInterface):
    def __init__(self, stream):
        self._stream = stream

    def read(self, max_bytes: int = None):
        # Print all incoming data to the terminal.
        data = self._stream.read(max_bytes)
        lines = data.decode('ascii', errors='replace').splitlines()
        for line in lines:
            print("<<< ", line)
        return data

    def write(self, data):
        # Print all outgoing data to the terminal.
        lines = data.decode('ascii', errors='replace').splitlines()
        for line in lines:
            print(">>> ", line)
        self._stream.write(data)

    def start_tls(ctx, hostname):
        self._stream.start_tls(ctx, hostname)

    def get_extra_info(key):
        return self._stream.get_extra_info(key)

    def close():
        self._stream.close()
```

```{ .python .ahttpx .hidden }
class RecordingBackend(ahhtpx.NetworkBackendInterface):
    def __init__(self):
        self._backend = NetworkBackend()

    async def connect(self, host, port):
        # Delegate creating connections to the default
        # network backend, and return a wrapped stream.
        stream = await self._backend.connect(host, port)
        return RecordingStream(stream)


class RecordingStream(ahttpx.NetworkStreamInterface):
    def __init__(self, stream):
        self._stream = stream

    async def read(self, max_bytes: int = None):
        # Print all incoming data to the terminal.
        data = await self._stream.read(max_bytes)
        lines = data.decode('ascii', errors='replace').splitlines()
        for line in lines:
            print("<<< ", line)
        return data

    async def write(self, data):
        # Print all outgoing data to the terminal.
        lines = data.decode('ascii', errors='replace').splitlines()
        for line in lines:
            print(">>> ", line)
        await self._stream.write(data)

    async def start_tls(ctx, hostname):
        await self._stream.start_tls(ctx, hostname)

    def get_extra_info(key):
        return self._stream.get_extra_info(key)

    async def close():
        await self._stream.close()
```

We can now instantiate a client using this network backend.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> transport = httpx.ConnectionPool(backend=RecordingBackend())
>>> cli = httpx.Client(transport=transport)
>>> cli.get('https://www.example.com')
```

```{ .python .ahttpx .hidden }
>>> transport = ahttpx.ConnectionPool(backend=RecordingBackend())
>>> cli = ahttpx.Client(transport=transport)
>>> await cli.get('https://www.example.com')
```

Custom network backends can also be used to provide functionality such as handling DNS caching for name lookups, or connecting via a UNIX domain socket instead of a TCP connection.

---

<span class="link-prev">← [Parsers](parsers.md)</span>
<span>&nbsp;</span>
