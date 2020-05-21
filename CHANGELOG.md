# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 0.13.0 (May 22nd, 2020)

This release switches to `httpcore` for all the internal networking, which means:

* We're using the same codebase for both our sync and async clients.
* HTTP/2 support is now available with the sync client.
* We no longer have a `urllib3` dependency for our sync client, although there is still an *optional* `URLLib3Transport` class.

It also means we've had to remove our UDS support, since maintaining that would have meant having to push back our work towards a 1.0 release, which isn't a trade-off we wanted to make.

We also now have [a public "Transport API"](https://www.python-httpx.org/advanced/#custom-transports), which you can use to implement custom transport implementations against. This formalises and replaces our previously private "Dispatch API".

### Changed

* Use `httpcore` for underlying HTTP transport. Drop `urllib3` requirement. (Pull #804, #967)
* Rename pool limit options from `soft_limit`/`hard_limit` to `max_keepalive`/`max_connections`. (Pull #968)
* The previous private "Dispatch API" has now been promoted to a public "Transport API". When customizing the transport use `transport=...`. The `ASGIDispatch` and `WSGIDispatch` class naming is deprecated in favour of `ASGITransport` and `WSGITransport`. (Pull #963)

### Added

* Added `URLLib3Transport` class for optional `urllib3` transport support. (Pull #804, #963)
* Streaming multipart uploads. (Pull #857)
* Logging via HTTPCORE_LOG_LEVEL and HTTPX_LOG_LEVEL environment variables
and TRACE level logging. (Pull encode/httpcore#79)

### Fixed

* Performance improvement in brotli decoder. (Pull #906)
* Proper warning level of deprecation notice in `Response.stream` and `Response.raw`. (Pull #908)
* Fix support for generator based WSGI apps. (Pull #887)
* Reuse of connections on HTTP/2 in close concurrency situations. (Pull encode/httpcore#81)
* Honor HTTP/2 max concurrent streams settings (Pull encode/httpcore#89, encode/httpcore#90)
* Fix bytes support in multipart uploads. (Pull #974)
* Improve typing support for `files=...`. (Pull #976)

### Removed

* Dropped support for `Client(uds=...)` (Pull #804)

## 0.13.0.dev2 (May 12th, 2020)

The 0.13.0.dev2 is a *pre-release* version. To install it, use `pip install httpx --pre`.

### Added

* Logging via HTTPCORE_LOG_LEVEL and HTTPX_LOG_LEVEL environment variables
and TRACE level logging. (HTTPCore Pull #79)

### Fixed

* Reuse of connections on HTTP/2 in close concurrency situations. (HTTPCore Pull #81)
* When using an `app=<ASGI app>` observe neater disconnect behaviour instead of sending empty body messages. (Pull #919)

## 0.13.0.dev1 (May 6th, 2020)

The 0.13.0.dev1 is a *pre-release* version. To install it, use `pip install httpx --pre`.

### Fixed

* Passing `http2` flag to proxy dispatchers. (Pull #934)
* Use [`httpcore` v0.8.3](https://github.com/encode/httpcore/releases/tag/0.8.3)
which addresses problems in handling of headers when using proxies.

## 0.13.0.dev0 (April 30th, 2020)

The 0.13.0.dev0 is a *pre-release* version. To install it, use `pip install httpx --pre`.

This release switches to `httpcore` for all the internal networking, which means:

* We're using the same codebase for both our sync and async clients.
* HTTP/2 support is now available with the sync client.
* We no longer have a `urllib3` dependency for our sync client, although there is still an *optional* `URLLib3Dispatcher` class.

It also means we've had to remove our UDS support, since maintaining that would have meant having to push back our work towards a 1.0 release, which isn't a trade-off we wanted to make.

### Changed

* Use `httpcore` for underlying HTTP transport. Drop `urllib3` requirement. (Pull #804)

### Added

* Added `URLLib3Dispatcher` class for optional `urllib3` transport support. (Pull #804)
* Streaming multipart uploads. (Pull #857)

### Fixed

* Performance improvement in brotli decoder. (Pull #906)
* Proper warning level of deprecation notice in `Response.stream` and `Response.raw`. (Pull #908)
* Fix support for generator based WSGI apps. (Pull #887)

### Removed

* Dropped support for `Client(uds=...)` (Pull #804)

## 0.12.1 (March 19th, 2020)

### Fixed

* Resolved packaging issue, where additional files were being included.

## 0.12.0 (March 9th, 2020)

The 0.12 release tightens up the API expectations for `httpx` by switching to private module names to enforce better clarity around public API.

All imports of `httpx` should import from the top-level package only, such as `from httpx import Request`, rather than importing from privately namespaced modules such as `from httpx._models import Request`.

### Added

* Support making response body available to auth classes with `.requires_response_body`. (Pull #803)
* Export `NetworkError` exception. (Pull #814)
* Add support for `NO_PROXY` environment variable. (Pull #835)

### Changed

* Switched to private module names. (Pull #785)
* Drop redirect looping detection and the `RedirectLoop` exception, instead using `TooManyRedirects`. (Pull #819)
* Drop `backend=...` parameter on `AsyncClient`, in favour of always autodetecting `trio`/`asyncio`. (Pull #791)

### Fixed

* Support basic auth credentials in proxy URLs. (Pull #780)
* Fix `httpx.Proxy(url, mode="FORWARD_ONLY")` configuration. (Pull #788)
* Fallback to setting headers as UTF-8 if no encoding is specified. (Pull #820)
* Close proxy dispatches classes on client close. (Pull #826)
* Support custom `cert` parameters even if `verify=False`. (Pull #796)
* Don't support invalid dict-of-dicts form data in `data=...`. (Pull #811)

## 0.11.1 (January 17th, 2020)

### Fixed

* Fixed usage of `proxies=...` on `Client()`. (Pull #763)
* Support both `zlib` and `deflate` style encodings on `Content-Encoding: deflate`. (Pull #758)
* Fix for streaming a redirect response body with `allow_redirects=False`. (Pull #766)
* Handle redirect with malformed Location headers missing host. (Pull #774)

## 0.11.0 (January 9th, 2020)

The 0.11 release reintroduces our sync support, so that `httpx` now supports both a standard thread-concurrency API, and an async API.

Existing async `httpx` users that are upgrading to 0.11 should ensure that:

* Async codebases should always use a client instance to make requests, instead of the top-level API.
* The async client is named as `httpx.AsyncClient()`, instead of `httpx.Client()`.
* When instantiating proxy configurations use the `httpx.Proxy()` class, instead of the previous `httpx.HTTPProxy()`. This new configuration class works for configuring both sync and async clients.

We believe the API is now pretty much stable, and are aiming for a 1.0 release sometime on or before April 2020.

### Changed

- Top level API such as `httpx.get(url, ...)`, `httpx.post(url, ...)`, `httpx.request(method, url, ...)` becomes synchronous.
- Added `httpx.Client()` for synchronous clients, with `httpx.AsyncClient` being used for async clients.
- Switched to `proxies=httpx.Proxy(...)` for proxy configuration.
- Network connection errors are wrapped in `httpx.NetworkError`, rather than exposing lower-level exception types directly.

### Removed

- The `request.url.origin` property and `httpx.Origin` class are no longer available.
- The per-request `cert`, `verify`, and `trust_env` arguments are escalated from raising errors if used, to no longer being available. These arguments should be used on a per-client instance instead, or in the top-level API.
- The `stream` argument has escalated from raising an error when used, to no longer being available. Use the `client.stream(...)` or `httpx.stream()` streaming API instead.

### Fixed

- Redirect loop detection matches against `(method, url)` rather than `url`. (Pull #734)

## 0.10.1 (December 31st, 2019)

### Fixed

- Fix issue with concurrent connection acquiry. (Pull #700)
- Fix write error on closing HTTP/2 connections. (Pull #699)

## 0.10.0 (December 29th, 2019)

The 0.10.0 release makes some changes that will allow us to support both sync and async interfaces.

In particular with streaming responses the `response.read()` method becomes `response.aread()`, and the `response.close()` method becomes `response.aclose()`.

If following redirects explicitly the `response.next()` method becomes `response.anext()`.

### Fixed

- End HTTP/2 streams immediately on no-body requests, rather than sending an empty body message. (Pull #682)
- Improve typing for `Response.request`: switch from `Optional[Request]` to `Request`. (Pull #666)
- `Response.elapsed` now reflects the entire download time. (Pull #687, #692)

### Changed

- Added `AsyncClient` as a synonym for `Client`. (Pull #680)
- Switch to `response.aread()` for conditionally reading streaming responses. (Pull #674)
- Switch to `response.aclose()` and `client.aclose()` for explicit closing. (Pull #674, #675)
- Switch to `response.anext()` for resolving the next redirect response. (Pull #676)

### Removed

- When using a client instance, the per-request usage of `verify`, `cert`, and `trust_env` have now escalated from raising a warning to raising an error. You should set these arguments on the client instead. (Pull #617)
- Removed the undocumented `request.read()`, since end users should not require it.

## 0.9.5 (December 20th, 2019)

### Fixed

- Fix Host header and HSTS rewrites when an explicit `:80` port is included in URL. (Pull #649)
- Query Params on the URL string are merged with any `params=...` argument. (Pull #653)
- More robust behavior when closing connections. (Pull #640)
- More robust behavior when handling HTTP/2 headers with trailing whitespace. (Pull #637)
- Allow any explicit `Content-Type` header to take precedence over the encoding default. (Pull #633)

## 0.9.4 (December 12th, 2019)

### Fixed

- Added expiry to Keep-Alive connections, resolving issues with acquiring connections. (Pull #627)
- Increased flow control windows on HTTP/2, resolving download speed issues. (Pull #629)

## 0.9.3 (December 7th, 2019)

### Fixed

- Fixed HTTP/2 with autodetection backend. (Pull #614)

## 0.9.2 (December 7th, 2019)

* Released due to packaging build artifact.

## 0.9.1 (December 6th, 2019)

* Released due to packaging build artifact.

## 0.9.0 (December 6th, 2019)

The 0.9 releases brings some major new features, including:

* A new streaming API.
* Autodetection of either asyncio or trio.
* Nicer timeout configuration.
* HTTP/2 support off by default, but can be enabled.

We've also removed all private types from the top-level package export.

In order to ensure you are only ever working with public API you should make
sure to only import the top-level package eg. `import httpx`, rather than
importing modules within the package.

### Added

- Added concurrency backend autodetection. (Pull #585)
- Added `Client(backend='trio')` and `Client(backend='asyncio')` API. (Pull #585)
- Added `response.stream_lines()` API. (Pull #575)
- Added `response.is_error` API. (Pull #574)
- Added support for `timeout=Timeout(5.0, connect_timeout=60.0)` styles. (Pull #593)

### Fixed

- Requests or Clients with `timeout=None` now correctly always disable timeouts. (Pull #592)
- Request 'Authorization' headers now have priority over `.netrc` authentication info. (Commit 095b691)
- Files without a filename no longer set a Content-Type in multipart data. (Commit ed94950)

### Changed

- Added `httpx.stream()` API. Using `stream=True` now results in a warning. (Pull #600, #610)
- HTTP/2 support is switched to "off by default", but can be enabled explicitly. (Pull #584)
- Switched to `Client(http2=True)` API from `Client(http_versions=["HTTP/1.1", "HTTP/2"])`. (Pull #586)
- Removed all private types from the top-level package export. (Pull #608)
- The SSL configuration settings of `verify`, `cert`, and `trust_env` now raise warnings if used per-request when using a Client instance. They should always be set on the Client instance itself. (Pull #597)
- Use plain strings "TUNNEL_ONLY" or "FORWARD_ONLY" on the HTTPProxy `proxy_mode` argument. The `HTTPProxyMode` enum still exists, but its usage will raise warnings. (#610)
- Pool timeouts are now on the timeout configuration, not the pool limits configuration. (Pull #563)
- The timeout configuration is now named `httpx.Timeout(...)`, not `httpx.TimeoutConfig(...)`. The old version currently remains as a synonym for backwards compatability.  (Pull #591)

## 0.8.0 (November 27, 2019)

### Removed

- The synchronous API has been removed, in order to allow us to fundamentally change how we approach supporting both sync and async variants. (See #588 for more details.)

## 0.7.8 (November 17, 2019)

### Added

- Add support for proxy tunnels for Python 3.6 + asyncio. (Pull #521)

## 0.7.7 (November 15, 2019)

### Fixed

- Resolve an issue with cookies behavior on redirect requests. (Pull #529)

### Added

- Add request/response DEBUG logs. (Pull #502)
- Use TRACE log level for low level info. (Pull #500)

## 0.7.6 (November 2, 2019)

### Removed

- Drop `proxies` parameter from the high-level API. (Pull #485)

### Fixed

- Tweak multipart files: omit null filenames, add support for `str` file contents. (Pull #482)
- Cache NETRC authentication per-client. (Pull #400)
- Rely on `getproxies` for all proxy environment variables. (Pull #470)
- Wait for the `asyncio` stream to close when closing a connection. (Pull #494)

## 0.7.5 (October 10, 2019)

### Added

- Allow lists of values to be passed to `params`. (Pull #386)
- `ASGIDispatch`, `WSGIDispatch` are now available in the `httpx.dispatch` namespace. (Pull #407)
- `HTTPError` is now available in the `httpx` namespace.  (Pull #421)
- Add support for `start_tls()` to the Trio concurrency backend. (Pull #467)

### Fixed

- Username and password are no longer included in the `Host` header when basic authentication
  credentials are supplied via the URL. (Pull #417)

### Removed

- The `.delete()` function no longer has `json`, `data`, or `files` parameters
  to match the expected semantics of the `DELETE` method. (Pull #408)
- Removed the `trio` extra. Trio support is detected automatically. (Pull #390)

## 0.7.4 (September 25, 2019)

### Added

- Add Trio concurrency backend. (Pull #276)
- Add `params` parameter to `Client` for setting default query parameters. (Pull #372)
- Add support for `SSL_CERT_FILE` and `SSL_CERT_DIR` environment variables. (Pull #307)
- Add debug logging to calls into ASGI apps. (Pull #371)
- Add debug logging to SSL configuration. (Pull #378)

### Fixed

- Fix a bug when using `Client` without timeouts in Python 3.6. (Pull #383)
- Propagate `Client` configuration to HTTP proxies. (Pull #377)

## 0.7.3 (September 20, 2019)

### Added

- HTTP Proxy support. (Pulls #259, #353)
- Add Digest authentication. (Pull #332)
- Add `.build_request()` method to `Client` and `AsyncClient`. (Pull #319)
- Add `.elapsed` property on responses. (Pull #351)
- Add support for `SSLKEYLOGFILE` in Python 3.8b4+. (Pull #301)

### Removed

- Drop NPN support for HTTP version negotiation. (Pull #314)

### Fixed

- Fix distribution of type annotations for mypy (Pull #361).
- Set `Host` header when redirecting cross-origin. (Pull #321)
- Drop `Content-Length` headers on `GET` redirects. (Pull #310)
- Raise `KeyError` if header isn't found in `Headers`. (Pull #324)
- Raise `NotRedirectResponse` in `response.next()` if there is no redirection to perform. (Pull #297)
- Fix bug in calculating the HTTP/2 maximum frame size. (Pull #153)

## 0.7.2 (August 28, 2019)

- Enforce using `httpx.AsyncioBackend` for the synchronous client. (Pull #232)
- `httpx.ConnectionPool` will properly release a dropped connection. (Pull #230)
- Remove the `raise_app_exceptions` argument from `Client`. (Pull #238)
- `DecodeError` will no longer be raised for an empty body encoded with Brotli. (Pull #237)
- Added `http_versions` parameter to `Client`. (Pull #250)
- Only use HTTP/1.1 on short-lived connections like `httpx.get()`. (Pull #284)
- Convert `Client.cookies` and `Client.headers` when set as a property. (Pull #274)
- Setting `HTTPX_DEBUG=1` enables debug logging on all requests. (Pull #277)

## 0.7.1 (August 18, 2019)

- Include files with source distribution to be installable. (Pull #233)

## 0.7.0 (August 17, 2019)

- Add the `trust_env` property to `BaseClient`. (Pull #187)
- Add the `links` property to `BaseResponse`. (Pull #211)
- Accept `ssl.SSLContext` instances into `SSLConfig(verify=...)`. (Pull #215)
- Add `Response.stream_text()` with incremental encoding detection. (Pull #183)
- Properly updated the `Host` header when a redirect changes the origin. (Pull #199)
- Ignore invalid `Content-Encoding` headers. (Pull #196)
- Use `~/.netrc` and `~/_netrc` files by default when `trust_env=True`. (Pull #189)
- Create exception base class `HTTPError` with `request` and `response` properties. (Pull #162)
- Add HSTS preload list checking within `BaseClient` to upgrade HTTP URLs to HTTPS. (Pull #184)
- Switch IDNA encoding from IDNA 2003 to IDNA 2008. (Pull #161)
- Expose base classes for alternate concurrency backends. (Pull #178)
- Improve Multipart parameter encoding. (Pull #167)
- Add the `headers` proeprty to `BaseClient`. (Pull #159)
- Add support for Google's `brotli` library. (Pull #156)
- Remove deprecated TLS versions (TLSv1 and TLSv1.1) from default `SSLConfig`. (Pull #155)
- Fix `URL.join(...)` to work similarly to RFC 3986 URL joining. (Pull #144)

## 0.6.8 (July 25, 2019)

- Check for disconnections when searching for an available
  connection in `ConnectionPool.keepalive_connections` (Pull #145)
- Allow string comparison for `URL` objects (Pull #139)
- Add HTTP status codes 418 and 451 (Pull #135)
- Add support for client certificate passwords (Pull #118)
- Enable post-handshake client cert authentication for TLSv1.3 (Pull #118)
- Disable using `commonName` for hostname checking for OpenSSL 1.1.0+ (Pull #118)
- Detect encoding for `Response.json()` (Pull #116)

## 0.6.7 (July 8, 2019)

- Check for connection aliveness on re-acquiry (Pull #111)

## 0.6.6 (July 3, 2019)

- Improve `USER_AGENT` (Pull #110)
- Add `Connection: keep-alive` by default to HTTP/1.1 connections. (Pull #110)

## 0.6.5 (June 27, 2019)

- Include `Host` header by default. (Pull #109)
- Improve HTTP protocol detection. (Pull #107)

## 0.6.4 (June 25, 2019)

- Implement read and write timeouts (Pull #104)

## 0.6.3 (June 24, 2019)

- Handle early connection closes (Pull #103)

## 0.6.2 (June 23, 2019)

- Use urllib3's `DEFAULT_CIPHERS` for the `SSLConfig` object. (Pull #100)

## 0.6.1 (June 21, 2019)

- Add support for setting a `base_url` on the `Client`.

## 0.6.0 (June 21, 2019)

- Honor `local_flow_control_window` for HTTP/2 connections (Pull #98)
