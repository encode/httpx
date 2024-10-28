# Extensions

Request and response extensions provide a untyped space where additional information may be added.

Extensions should be used for features that may not be available on all transports, and that do not fit neatly into [the simplified request/response model](https://www.encode.io/httpcore/extensions/) that the underlying `httpcore` package uses as its API.

Several extensions are supported on the request:

```python
# Request timeouts actually implemented as an extension on
# the request, ensuring that they are passed throughout the
# entire call stack.
client = httpx.Client()
response = client.get(
    "https://www.example.com",
    extensions={"timeout": {"connect": 5.0}}
)
response.request.extensions["timeout"]
{"connect": 5.0}
```

And on the response:

```python
client = httpx.Client()
response = client.get("https://www.example.com")
print(response.extensions["http_version"])  # b"HTTP/1.1"
# Other server responses could have been
# b"HTTP/0.9", b"HTTP/1.0", or b"HTTP/1.1"
```

## Request Extensions

### `"trace"`

The trace extension allows a callback handler to be installed to monitor the internal
flow of events within the underlying `httpcore` transport.

The simplest way to explain this is with an example:

```python
import httpx

def log(event_name, info):
    print(event_name, info)

client = httpx.Client()
response = client.get("https://www.example.com/", extensions={"trace": log})
# connection.connect_tcp.started {'host': 'www.example.com', 'port': 443, 'local_address': None, 'timeout': None}
# connection.connect_tcp.complete {'return_value': <httpcore.backends.sync.SyncStream object at 0x1093f94d0>}
# connection.start_tls.started {'ssl_context': <ssl.SSLContext object at 0x1093ee750>, 'server_hostname': b'www.example.com', 'timeout': None}
# connection.start_tls.complete {'return_value': <httpcore.backends.sync.SyncStream object at 0x1093f9450>}
# http11.send_request_headers.started {'request': <Request [b'GET']>}
# http11.send_request_headers.complete {'return_value': None}
# http11.send_request_body.started {'request': <Request [b'GET']>}
# http11.send_request_body.complete {'return_value': None}
# http11.receive_response_headers.started {'request': <Request [b'GET']>}
# http11.receive_response_headers.complete {'return_value': (b'HTTP/1.1', 200, b'OK', [(b'Age', b'553715'), (b'Cache-Control', b'max-age=604800'), (b'Content-Type', b'text/html; charset=UTF-8'), (b'Date', b'Thu, 21 Oct 2021 17:08:42 GMT'), (b'Etag', b'"3147526947+ident"'), (b'Expires', b'Thu, 28 Oct 2021 17:08:42 GMT'), (b'Last-Modified', b'Thu, 17 Oct 2019 07:18:26 GMT'), (b'Server', b'ECS (nyb/1DCD)'), (b'Vary', b'Accept-Encoding'), (b'X-Cache', b'HIT'), (b'Content-Length', b'1256')])}
# http11.receive_response_body.started {'request': <Request [b'GET']>}
# http11.receive_response_body.complete {'return_value': None}
# http11.response_closed.started {}
# http11.response_closed.complete {'return_value': None}
```

The `event_name` and `info` arguments here will be one of the following:

* `{event_type}.{event_name}.started`, `<dictionary of keyword arguments>`
* `{event_type}.{event_name}.complete`, `{"return_value": <...>}`
* `{event_type}.{event_name}.failed`, `{"exception": <...>}`

Note that when using async code the handler function passed to `"trace"` must be an `async def ...` function.

The following event types are currently exposed...

**Establishing the connection**

* `"connection.connect_tcp"`
* `"connection.connect_unix_socket"`
* `"connection.start_tls"`

**HTTP/1.1 events**

* `"http11.send_request_headers"`
* `"http11.send_request_body"`
* `"http11.receive_response"`
* `"http11.receive_response_body"`
* `"http11.response_closed"`

**HTTP/2 events**

* `"http2.send_connection_init"`
* `"http2.send_request_headers"`
* `"http2.send_request_body"`
* `"http2.receive_response_headers"`
* `"http2.receive_response_body"`
* `"http2.response_closed"`

The exact set of trace events may be subject to change across different versions of `httpcore`. If you need to rely on a particular set of events it is recommended that you pin installation of the package to a fixed version.

### `"sni_hostname"`

The server's hostname, which is used to confirm the hostname supplied by the SSL certificate.

If you want to connect to an explicit IP address rather than using the standard DNS hostname lookup, then you'll need to use this request extension.

For example:

``` python
# Connect to '185.199.108.153' but use 'www.encode.io' in the Host header,
# and use 'www.encode.io' when SSL verifying the server hostname.
client = httpx.Client()
headers = {"Host": "www.encode.io"}
extensions = {"sni_hostname": "www.encode.io"}
response = client.get(
    "https://185.199.108.153/path",
    headers=headers,
    extensions=extensions
)
```

### `"timeout"`

A dictionary of `str: Optional[float]` timeout values.

May include values for `'connect'`, `'read'`, `'write'`, or `'pool'`.

For example:

```python
# Timeout if a connection takes more than 5 seconds to established, or if
# we are blocked waiting on the connection pool for more than 10 seconds.
client = httpx.Client()
response = client.get(
    "https://www.example.com",
    extensions={"timeout": {"connect": 5.0, "pool": 10.0}}
)
```

This extension is how the `httpx` timeouts are implemented, ensuring that the timeout values are associated with the request instance and passed throughout the stack. You shouldn't typically be working with this extension directly, but use the higher level `timeout` API instead.

### `"target"`

The target that is used as [the HTTP target instead of the URL path](https://datatracker.ietf.org/doc/html/rfc2616#section-5.1.2).

This enables support constructing requests that would otherwise be unsupported.

* URL paths with non-standard escaping applied.
* Forward proxy requests using an absolute URI.
* Tunneling proxy requests using `CONNECT` with hostname as the target.
* Server-wide `OPTIONS *` requests.

Some examples:

Using the 'target' extension to send requests without the standard path escaping rules...

```python
# Typically a request to "https://www.example.com/test^path" would
# connect to "www.example.com" and send an HTTP/1.1 request like...
#
# GET /test%5Epath HTTP/1.1
#
# Using the target extension we can include the literal '^'...
#
# GET /test^path HTTP/1.1
#
# Note that requests must still be valid HTTP requests.
# For example including whitespace in the target will raise a `LocalProtocolError`.
extensions = {"target": b"/test^path"}
response = httpx.get("https://www.example.com", extensions=extensions)
```

The `target` extension also allows server-wide `OPTIONS *` requests to be constructed...

```python
# This will send the following request...
#
# CONNECT * HTTP/1.1
extensions = {"target": b"*"}
response = httpx.request("CONNECT", "https://www.example.com", extensions=extensions)
```

## Response Extensions

### `"http_version"`

The HTTP version, as bytes. Eg. `b"HTTP/1.1"`.

When using HTTP/1.1 the response line includes an explicit version, and the value of this key could feasibly be one of `b"HTTP/0.9"`, `b"HTTP/1.0"`, or `b"HTTP/1.1"`.

When using HTTP/2 there is no further response versioning included in the protocol, and the value of this key will always be `b"HTTP/2"`.

### `"reason_phrase"`

The reason-phrase of the HTTP response, as bytes. For example `b"OK"`. Some servers may include a custom reason phrase, although this is not recommended.

HTTP/2 onwards does not include a reason phrase on the wire.

When no key is included, a default based on the status code may be used.

### `"stream_id"`

When HTTP/2 is being used the `"stream_id"` response extension can be accessed to determine the ID of the data stream that the response was sent on.

### `"network_stream"`

The `"network_stream"` extension allows developers to handle HTTP `CONNECT` and `Upgrade` requests, by providing an API that steps outside the standard request/response model, and can directly read or write to the network.

The interface provided by the network stream:

* `read(max_bytes, timeout = None) -> bytes`
* `write(buffer, timeout = None)`
* `close()`
* `start_tls(ssl_context, server_hostname = None, timeout = None) -> NetworkStream`
* `get_extra_info(info) -> Any`

This API can be used as the foundation for working with HTTP proxies, WebSocket upgrades, and other advanced use-cases.

See the [network backends documentation](https://www.encode.io/httpcore/network-backends/) for more information on working directly with network streams.

**Extra network information**

The network stream abstraction also allows access to various low-level information that may be exposed by the underlying socket:

```python
response = httpx.get("https://www.example.com")
network_stream = response.extensions["network_stream"]

client_addr = network_stream.get_extra_info("client_addr")
server_addr = network_stream.get_extra_info("server_addr")
print("Client address", client_addr)
print("Server address", server_addr)
```

The socket SSL information is also available through this interface, although you need to ensure that the underlying connection is still open, in order to access it...

```python
with httpx.stream("GET", "https://www.example.com") as response:
    network_stream = response.extensions["network_stream"]

    ssl_object = network_stream.get_extra_info("ssl_object")
    print("TLS version", ssl_object.version())
```
