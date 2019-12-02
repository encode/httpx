<p align="center">
  <a href="https://www.encode.io/httpx/"><img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/logo.jpg" alt='HTTPX'></a>
</p>

<p align="center"><strong>HTTPX</strong> <em>- A next-generation HTTP client for Python.</em></p>

<p align="center">
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

HTTPX is an asynchronous HTTP client, that supports HTTP/2 and HTTP/1.1.

It can be used in high-performance async web frameworks, using either asyncio
or trio, and is able to support making large numbers of requests concurrently.

**Note**: *The 0.8 release switched HTTPX into focusing exclusively on the async
client. It is possible that we'll look at re-introducing a sync API at a
later date.*

---

Let's get started...

*The standard Python REPL does not allow top-level async statements.*

*To run async examples directly you'll probably want to either use `ipython`,
or use Python 3.8 with `python -m asyncio`.*

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

HTTPX builds on the well-established usability of `requests`, and gives you:

* A requests-compatible API wherever possible.
* HTTP/2 and HTTP/1.1 support.
* Ability to [make requests directly to ASGI applications](https://www.encode.io/httpx/advanced/#calling-into-python-web-apps).
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

## Installation

Install with pip:

```shell
$ pip install httpx
```

httpx requires Python 3.6+

## Documentation

Project documentation is available at [www.encode.io/httpx/](https://www.encode.io/httpx/).

For a run-through of all the basics, head over to the [QuickStart](https://www.encode.io/httpx/quickstart/).

For more advanced topics, see the [Advanced Usage](https://www.encode.io/httpx/advanced/) section.

The [Developer Interface](https://www.encode.io/httpx/api/) provides a comprehensive API reference.

## Contribute

If you want to contribute with HTTPX check out the [Contributing Guide](https://www.encode.io/httpx/contributing/) to learn how to start.

## Dependencies

The httpx project relies on these excellent libraries:

* `h2` - HTTP/2 support.
* `h11` - HTTP/1.1 support.
* `certifi` - SSL certificates.
* `chardet` - Fallback auto-detection for response encoding.
* `hstspreload` - determines whether IDNA-encoded host should be only accessed via HTTPS.
* `idna` - Internationalized domain name support.
* `rfc3986` - URL parsing & normalization.
* `sniffio` - Async library autodetection.
* `brotlipy` - Decoding for "brotli" compressed responses. *(Optional)*

A huge amount of credit is due to `requests` for the API layout that
much of this work follows, as well as to `urllib3` for plenty of design
inspiration around the lower-level networking details.

<p align="center">&mdash; ⭐️ &mdash;</p>
<p align="center"><i>HTTPX is <a href="https://github.com/encode/httpx/blob/master/LICENSE.md">BSD licensed</a> code. Designed & built in Brighton, England.</i></p>
