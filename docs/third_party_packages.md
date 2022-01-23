# Third Party Packages

As HTTPX usage grows, there is an expanding community of developers building tools and libraries that integrate with HTTPX, or depend on HTTPX. Here are some of them.

## Plugins

<!-- NOTE: this list is in alphabetical order. -->

### Authlib

[GitHub](https://github.com/lepture/authlib) - [Documentation](https://docs.authlib.org/en/latest/)

The ultimate Python library in building OAuth and OpenID Connect clients and servers. Includes an [OAuth HTTPX client](https://docs.authlib.org/en/latest/client/httpx.html).

### Gidgethub

[GitHub](https://github.com/brettcannon/gidgethub) - [Documentation](https://gidgethub.readthedocs.io/en/latest/index.html)

An asynchronous GitHub API library. Includes [HTTPX support](https://gidgethub.readthedocs.io/en/latest/httpx.html).

### HTTPX-Auth

[GitHub](https://github.com/Colin-b/httpx_auth) - [Documentation](https://colin-b.github.io/httpx_auth/)

Provides authentication classes to be used with HTTPX [authentication parameter](advanced.md#customizing-authentication).

### pytest-HTTPX

[GitHub](https://github.com/Colin-b/pytest_httpx) - [Documentation](https://colin-b.github.io/pytest_httpx/)

Provides `httpx_mock` [pytest](https://docs.pytest.org/en/latest/) fixture to mock HTTPX within test cases.

### RESPX

[GitHub](https://github.com/lundberg/respx) - [Documentation](https://lundberg.github.io/respx/)

A utility for mocking out the Python HTTPX library.

### rpc.py

[Github](https://github.com/abersheeran/rpc.py) - [Documentation](https://github.com/abersheeran/rpc.py#rpcpy)

An fast and powerful RPC framework based on ASGI/WSGI. Use HTTPX as the client of the RPC service.

### VCR.py

[GitHub](https://github.com/kevin1024/vcrpy) - [Documentation](https://vcrpy.readthedocs.io/)

A utility for record and repeat an http request.

### httpx-caching

[Github](https://github.com/johtso/httpx-caching)

This package adds caching functionality to HTTPX

## Gists

<!-- NOTE: this list is in alphabetical order. -->

### urllib3-transport

[GitHub](https://gist.github.com/florimondmanca/d56764d78d748eb9f73165da388e546e)

This public gist provides an example implementation for a [custom transport](advanced.md#custom-transports) implementation on top of the battle-tested [`urllib3`](https://urllib3.readthedocs.io) library.
