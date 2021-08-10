<p align="center" style="margin: 0 0 10px">
  <img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/butterfly.png" alt='HTTPX'>
</p>

<h1 align="center" style="font-size: 3rem; margin: -15px 0">
HTTPX
</h1>

---

<div align="center">
<p>
<a href="https://github.com/encode/httpx/actions">
    <img src="https://github.com/encode/httpx/workflows/Test%20Suite/badge.svg" alt="Test Suite">
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

    We believe we've got the public API to a stable point now, but would strongly recommend pinning your dependencies to the `0.18.*` release, so that you're able to properly review [API changes between package updates](https://github.com/encode/httpx/blob/master/CHANGELOG.md).

    A 1.0 release is expected to be issued sometime in 2021.

---

Let's get started...

```pycon
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

Or, using the async API...

_Use [IPython](https://ipython.readthedocs.io/en/stable/) or Python 3.8+ with `python -m asyncio` to try this code interactively._

```pycon
>>> import httpx
>>> async with httpx.AsyncClient() as client:
...     r = await client.get('https://www.example.org/')
...
>>> r
<Response [200 OK]>
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
the [async support](async.md) section, or the [HTTP/2](http2.md) section.

The [Developer Interface](api.md) provides a comprehensive API reference.

To find out about tools that integrate with HTTPX, see [Third Party Packages](third_party_packages.md).

## Dependencies

The HTTPX project relies on these excellent libraries:

* `httpcore` - The underlying transport implementation for `httpx`.
  * `h11` - HTTP/1.1 support.
  * `h2` - HTTP/2 support. *(Optional)*
* `certifi` - SSL certificates.
* `charset_normalizer` - Charset auto-detection.
* `rfc3986` - URL parsing & normalization.
  * `idna` - Internationalized domain name support.
* `sniffio` - Async library autodetection.
* `async_generator` - Backport support for `contextlib.asynccontextmanager`. *(Only required for Python 3.6)*
* `brotlicffi` - Decoding for "brotli" compressed responses. *(Optional)*

A huge amount of credit is due to `requests` for the API layout that
much of this work follows, as well as to `urllib3` for plenty of design
inspiration around the lower-level networking details.

## Installation

Install with pip:

```shell
$ pip install httpx
```

Or, to include the optional HTTP/2 support, use:

```shell
$ pip install httpx[http2]
```

To include the optional brotli decoder support, use:

```shell
$ pip install httpx[brotli]
```

HTTPX requires Python 3.6+

[sync-support]: https://github.com/encode/httpx/issues/572
