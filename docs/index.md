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

HTTPX is an asynchronous client library that supports HTTP/1.1 and HTTP/2.

It can be used in high-performance async web frameworks, using either asyncio
or trio, and is able to support making large numbers of concurrent requests.

!!! note
    HTTPX should currently be considered in alpha. We'd love early users and feedback,
    but would strongly recommend pinning your dependencies to the latest median
    release, so that you're able to properly review API changes between package
    updates. Currently you should be using `httpx==0.9.*`.

    In particular, the 0.8 release switched HTTPX into focusing exclusively on
    providing an async client, in order to move the project forward, and help
    us [change our approach to providing sync+async support][sync-support]. If
    you have been using the sync client, you may want to pin to `httpx==0.7.*`,
    and wait until our sync client is reintroduced.

---

Let's get started...

The standard Python REPL does not allow top-level async statements.

To run these async examples you'll probably want to either use `ipython`,
or use Python 3.8 with `python -m asyncio`.

```python
>>> import httpx
>>> r = await httpx.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.http_version
'HTTP/1.1'
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

## Features

HTTPX is a high performance asynchronous HTTP client, that builds on the
well-established usability of `requests`, and gives you:

* A broadly requests-compatible API.
* HTTP/1.1 and [HTTP/2 support](http2.md).
* Ability to [make requests directly to ASGI applications](advanced.md#calling-into-python-web-apps).
* Strict timeouts everywhere.
* Fully type annotated.
* 100% test coverage.

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
or the [HTTP/2](http2.md) section.

The [Developer Interface](api.md) provides a comprehensive API reference.

## Dependencies

The HTTPX project relies on these excellent libraries:

* `h2` - HTTP/2 support.
* `h11` - HTTP/1.1 support.
* `certifi` - SSL certificates.
* `charset_normalizer` - Fallback auto-detection for response encoding.
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
