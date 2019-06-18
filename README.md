# HTTP3

<a href="https://travis-ci.org/encode/http3">
    <img src="https://travis-ci.org/encode/http3.svg?branch=master" alt="Build Status">
</a>
<a href="https://codecov.io/gh/encode/http3">
    <img src="https://codecov.io/gh/encode/http3/branch/master/graph/badge.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/http3/">
    <img src="https://badge.fury.io/py/http3.svg" alt="Package version">
</a>

HTTP3 is a next-generation HTTP client for Python 3.

**Note**: *This project should be considered as an "alpha" release. It is substantially API complete, but there are still some areas that need more work.*

---

Let's get started...

```python
>>> import http3
>>> r = http3.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.protocol
'HTTP/2'
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

## Features

HTTP3 builds on the well-established usability of `requests`, and gives you:

* A requests-compatible API.
* HTTP/2 and HTTP/1.1 support.
* Support for [issuing HTTP requests in parallel](https://www.encode.io/http3/parallel/). *(Coming soon)*
* Standard synchronous interface, but [with `async`/`await` support if you need it](https://www.encode.io/http3/async/).
* Ability to [make requests directly to WSGI or ASGI applications](https://www.encode.io/http3/advanced/#calling-into-python-web-apps).
* Strict timeouts everywhere.
* Fully type annotated.
* 100% test coverage.

Plus all the standard features of `requests`...

* International Domains and URLs
* Keep-Alive & Connection Pooling
* Sessions with Cookie Persistence
* Browser-style SSL Verification
* Basic/Digest Authentication *(Digest is still TODO)*
* Elegant Key/Value Cookies
* Automatic Decompression
* Automatic Content Decoding
* Unicode Response Bodies
* Multipart File Uploads
* HTTP(S) Proxy Support *(TODO)*
* Connection Timeouts
* Streaming Downloads
* .netrc Support *(TODO)*
* Chunked Requests

## Installation

Install with pip:

```shell
$ pip install http3
```

HTTP3 requires Python 3.6+

## Documentation

Project documentation is available at [www.encode.io/http3/](https://www.encode.io/http3/).

For a run-through of all the basics, head over to the [QuickStart](https://www.encode.io/http3/quickstart/).

For more advanced topics, see the [Advanced Usage](https://www.encode.io/http3/advanced/) section, or
the specific topics on making [Parallel Requests](https://www.encode.io/http3/parallel/) or using the
[Async Client](https://www.encode.io/http3/async/).

The [Developer Interface](https://www.encode.io/http3/api/) provides a comprehensive API reference.

## Dependencies

The HTTP3 project relies on these excellent libraries:

* `h2` - HTTP/2 support.
* `h11` - HTTP/1.1 support.
* `certifi` - SSL certificates.
* `chardet` - Fallback auto-detection for response encoding.
* `idna` - Internationalized domain name support.
* `rfc3986` - URL parsing & normalization.
* `brotlipy` - Decoding for "brotli" compressed responses. *(Optional)*

A huge amount of credit is due to `requests` for the API layout that
much of this work follows, as well as to `urllib3` for plenty of design
inspiration around the lower level networking details.

<p align="center">&mdash; ⭐️ &mdash;</p>
<p align="center"><i>HTTP3 is <a href="https://github.com/encode/http3/blob/master/LICENSE.md">BSD licensed</a> code. Designed & built in Brighton, England.</i></p>
