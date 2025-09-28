# Third Party Packages

As HTTPX usage grows, there is an expanding community of developers building tools and libraries that integrate with HTTPX, or depend on HTTPX. Here are some of them.

<!-- NOTE: Entries are alphabetised. -->

## Plugins

### Hishel

[GitHub](https://github.com/karpetrosyan/hishel) - [Documentation](https://hishel.com/)

An elegant HTTP Cache implementation for HTTPX and HTTP Core.

### HTTPX-Auth

[GitHub](https://github.com/Colin-b/httpx_auth) - [Documentation](https://colin-b.github.io/httpx_auth/)

Provides authentication classes to be used with HTTPX's [authentication parameter](advanced/authentication.md#customizing-authentication).

### httpx-caching

[Github](https://github.com/johtso/httpx-caching)

This package adds caching functionality to HTTPX

### httpx-secure

[GitHub](https://github.com/Zaczero/httpx-secure)

Drop-in SSRF protection for httpx with DNS caching and custom validation support.

### httpx-socks

[GitHub](https://github.com/romis2012/httpx-socks)

Proxy (HTTP, SOCKS) transports for httpx.

### httpx-sse

[GitHub](https://github.com/florimondmanca/httpx-sse)

Allows consuming Server-Sent Events (SSE) with HTTPX.

### httpx-retries

[GitHub](https://github.com/will-ockmore/httpx-retries) - [Documentation](https://will-ockmore.github.io/httpx-retries/)

A retry layer for HTTPX.

### httpx-ws

[GitHub](https://github.com/frankie567/httpx-ws) - [Documentation](https://frankie567.github.io/httpx-ws/)

WebSocket support for HTTPX.

### pytest-HTTPX

[GitHub](https://github.com/Colin-b/pytest_httpx) - [Documentation](https://colin-b.github.io/pytest_httpx/)

Provides a [pytest](https://docs.pytest.org/en/latest/) fixture to mock HTTPX within test cases.

### RESPX

[GitHub](https://github.com/lundberg/respx) - [Documentation](https://lundberg.github.io/respx/)

A utility for mocking out HTTPX.

### rpc.py

[Github](https://github.com/abersheeran/rpc.py) - [Documentation](https://github.com/abersheeran/rpc.py#rpcpy)

A fast and powerful RPC framework based on ASGI/WSGI. Use HTTPX as the client of the RPC service.

## Libraries with HTTPX support

### Authlib

[GitHub](https://github.com/lepture/authlib) - [Documentation](https://docs.authlib.org/en/latest/)

A python library for building OAuth and OpenID Connect clients and servers. Includes an [OAuth HTTPX client](https://docs.authlib.org/en/latest/client/httpx.html).

### Gidgethub

[GitHub](https://github.com/brettcannon/gidgethub) - [Documentation](https://gidgethub.readthedocs.io/en/latest/index.html)

An asynchronous GitHub API library. Includes [HTTPX support](https://gidgethub.readthedocs.io/en/latest/httpx.html).

### httpdbg

[GitHub](https://github.com/cle-b/httpdbg) - [Documentation](https://httpdbg.readthedocs.io/)

A tool for python developers to easily debug the HTTP(S) client requests in a python program.

### VCR.py

[GitHub](https://github.com/kevin1024/vcrpy) - [Documentation](https://vcrpy.readthedocs.io/)

Record and repeat requests.

## Gists

### urllib3-transport

[GitHub](https://gist.github.com/florimondmanca/d56764d78d748eb9f73165da388e546e)

This public gist provides an example implementation for a [custom transport](advanced/transports.md#custom-transports) implementation on top of the battle-tested [`urllib3`](https://urllib3.readthedocs.io) library.
