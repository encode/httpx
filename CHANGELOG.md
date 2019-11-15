# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
