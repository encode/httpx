<p align="center" style="margin: 0 0 10px">
  <img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/logo.jpg" alt='HTTPX'>
</p>

<h1 align="center" style="font-size: 3rem; margin: -15px 0">
HTTPX
</h1>

---

<div align="center">
<p>
<a href="https://travis-ci.org/encode/httpx">
    <img src="https://travis-ci.org/encode/httpx.svg?branch=master" alt="Build Status">
</a>
<a href="https://codecov.io/gh/encode/httpx">
    <img src="https://codecov.io/gh/encode/httpx/branch/master/graph/badge.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/httpx/">
    <img src="https://badge.fury.io/py/httpx.svg" alt="Package version">
</a>
</p>

<em>A next-generation HTTP client for Python.</em>
</div>

HTTPX is a fully featured HTTP client for Python 3, which provides sync and async APIs, and support for both HTTP/1.1 and HTTP/2.


!!! note
    HTTPX should currently be considered in beta.

    We believe we've got the public API to a stable point now, but would strongly recommend pinning your dependencies to the `0.11.*` release, so that you're able to properly review [API changes between package updates](https://github.com/encode/httpx/blob/master/CHANGELOG.md).

    A 1.0 release is expected to be issued sometime on or before April 2020.

---

Let's get started...

```python
>>> import httpx
>>> r = httpx.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

## Features

HTTPX is a high performance asynchronous HTTP client, that builds on the
well-established usability of `requests`, and gives you:

* A broadly [requests-compatible API](compatibility.md).
* Standard synchronous interface, but with [async support if you need it](async.md).
* HTTP/1.1 [and HTTP/2 support](http2.md).
* Ability to make requests directly to [WSGI applications](advanced.md#calling-into-python-web-apps) or [ASGI applications](async.md#calling-into-python-web-apps).
* Strict timeouts everywhere.
* Fully type annotated.
* 99% test coverage.

Plus all the standard features of `requests`...

* International Domains and URLs
* Keep-Alive & Connection Pooling
* Sessions with Cookie Persistence
* Browser-style SSL Verification
* Basic/Digest Authentication
* Elegant Key/Value Cookies
* Automatic Decompression
* Automatic Content Decoding
* Unicode Response Bodies
* Multipart File Uploads
* HTTP(S) Proxy Support
* Connection Timeouts
* Streaming Downloads
* .netrc Support
* Chunked Requests

## Documentation

For a run-through of all the basics, head over to the [QuickStart](quickstart.md).

For more advanced topics, see the [Advanced Usage](advanced.md) section,
the [async support](async.md) section, or the [HTTP/2](http2.md) section.

The [Developer Interface](api.md) provides a comprehensive API reference.

## Dependencies

The HTTPX project relies on these excellent libraries:

* `urllib3` - Sync client support.
* `h11` - HTTP/1.1 support.
* `h2` - HTTP/2 support.
* `certifi` - SSL certificates.
* `chardet` - Fallback auto-detection for response encoding.
* `hstspreload` - determines whether IDNA-encoded host should be only accessed via HTTPS.
* `idna` - Internationalized domain name support.
* `rfc3986` - URL parsing & normalization.
* `brotlipy` - Decoding for "brotli" compressed responses. *(Optional)*

A huge amount of credit is due to `requests` for the API layout that
much of this work follows, as well as to `urllib3` for plenty of design
inspiration around the lower-level networking details.

## Installation

Install with pip:

```shell
$ pip install httpx
```

HTTPX requires Python 3.6+

[sync-support]: https://github.com/encode/httpx/issues/572
