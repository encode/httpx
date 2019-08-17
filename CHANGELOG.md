# Changelog

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
