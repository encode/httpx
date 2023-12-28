## Top level API

### Specific HTTP method calls

* `httpx.get()`
* `httpx.post()`
* `httpx.put()`
* `httpx.patch()`
* `httpx.delete()`
* `httpx.head()`
* `httpx.options()`

### General HTTP requests

* `httpx.request()`
* `httpx.stream()`

## Requests & Responses

* `httpx.URL()`
* `httpx.QueryParams()`
* `httpx.Headers()`
* `httpx.Cookies()`
* `httpx.Request()`
* `httpx.Response()`

## Clients

* `httpx.Client()`
* `httpx.AsyncClient()`

### Authentication

* `httpx.Auth()`
* `httpx.BasicAuth()`
* `httpx.DigestAuth()`
* `httpx.NetRCAuth()`

### Configuration

* `httpx.SSLContext()`  # TODO
* `httpx.Limits()`
* `httpx.Proxy()`
* `httpx.Timeout()`
* `httpx.NetworkOptions()`  # TODO
* `httpx.HTTPVersion()`  # TODO

### Transport classes

* `httpx.HTTPTransport()`
* `httpx.AsyncHTTPTransport()`
* `httpx.ASGITransport()`
* `httpx.WSGITransport()`
* `httpx.MockTransport()`
* `httpx.BaseTransport()`
* `httpx.AsyncBaseTransport()`

## Command Line Client

* `httpx.main()`

### Misc...

codes
ByteStream
AsyncByteStream
SyncByteStream
USE_CLIENT_DEFAULT
create_ssl_context

* `httpx.MountPoints()`  # TODO
* `httpx.get_env_proxies()`  # TODO


Oh hai

* Timing information
* Download and upload progress
* importing

* sni_hostname / --verbose, trace, net / note on alpn and http/2

* dns caching

* `read()` within `send_single_request()`