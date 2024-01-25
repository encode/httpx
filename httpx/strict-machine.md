### 1.0, Strict Machine

HTTPX 1.0 includes a number of breaking API changes. These have been made in order to present a simplified and more consistent API throughout.

The following API changes effect how the `HTTPTransport` instance on the client is configured, and have all been simplified...

* The `cert` and `verify` parameters are no longer supported. Use `ssl_context=httpx.SSLContext(verify=..., cert=...)`.
* The `proxies={...}` parameter is no longer supported. Use `proxy=httpx.Proxy(...)`. TODO: describe proxy routing / env.
* The `http1` and `http2` parameters are no longer supported. Use `version=httpx.Version("HTTP/1.1", "HTTP/2")`.
* The `uds`, `local_address`, `retries`, and `socket_options` parameters are no longer supported. Use `network_options=httpx.NetworkOptions()`.
* The `app` shortcut is no longer supported. Use the explicit style of `transport=httpx.WSGITransport()` or `transport=httpx.ASGITransport()`.

The following parameters have been made stricter, and no longer allow shortcut usages...

* The `auth` parameter should now always be an `httpx.Auth()` instance. The `(username, password)` and `callable(request) -> response` shortcuts are no longer supported.
* The `timeout` parameter should now always be an `httpx.Timeout()` instance. The `float` and `None` shortcuts are no longer supported. Use `httpx.Timeout('inf')` to disable timeouts.
* The `proxy` parameter should now always be an `httpx.Proxy()` instance. The `str` shortcut is no longer supported. HTTPS proxxy configurations must have an `ssl_context` applied.

The following functionality was previously built directly into `httpx.Client`, and is now replaced with a transport instance...

* The `mounts` parameter is no longer supported. Use `transport=httpx.Mounts()`.

The following has been removed...

* The `Response.elapsed` property no longer exists. You can use event hooks to implement this functionality.

### New functionality

* Added `client.transport`.

### Environment variables

HTTPX 1.0 no longer includes *any* automatic configuration based on environment variables.

* The `trust_env` parameter no longer exists.
* The `SSL_CERT_FILE`, `SSL_CERT_DIR`, and `SSLKEYLOGFILE` environment variables are no longer automatically applied. See the SSL documentation for information on how to enable them.
* The `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY` environment variables are no longer automatically applied. See the Proxy documentation for information on how to enable them.

### Requirements

...

---

* DNS caching
* HTTP/3
* Drop `anyio` requirement?
* Resource limiting. (response max size, response timeout)
* `.read()` streaming.
* Cookies enable/disable and performance.
* Avoid auth flow when no auth enabled.
* `httpx.Redirects` ???
* `network_backend` in `NetworkOptions`
* Response read for event hooks.

* `ssl_context` required for `Proxy("https://...")` (and required to not exist for "http")?

* Add Transport example for... rotating proxies.