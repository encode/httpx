# Environment Variables

The HTTPX library can be configured via environment variables.
Environment variables are used by default. To ignore environment variables, `trust_env` has to be set `False`. There are two ways to set `trust_env` to disable environment variables:

* On the client via `httpx.Client(trust_env=False)`.
* Using the top-level API, such as `httpx.get("<url>", trust_env=False)`.

Here is a list of environment variables that HTTPX recognizes and what function they serve:

## Proxies

The environment variables documented below are used as a convention by various HTTP tooling, including:

* [cURL](https://github.com/curl/curl/blob/master/docs/MANUAL.md#environment-variables)
* [requests](https://github.com/psf/requests/blob/master/docs/user/advanced.rst#proxies)

For more information on using proxies in HTTPX, see [HTTP Proxying](advanced/proxies.md#http-proxying).

### `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`

Valid values: A URL to a proxy

`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` set the proxy to be used for `http`, `https`, or all requests respectively.

```bash
export HTTP_PROXY=http://my-external-proxy.com:1234

# This request will be sent through the proxy
python -c "import httpx; httpx.get('http://example.com')"

# This request will be sent directly, as we set `trust_env=False`
python -c "import httpx; httpx.get('http://example.com', trust_env=False)"

```

### `NO_PROXY`

Valid values: a comma-separated list of hostnames/urls

`NO_PROXY` disables the proxy for specific urls

```bash
export HTTP_PROXY=http://my-external-proxy.com:1234
export NO_PROXY=http://127.0.0.1,python-httpx.org

# As in the previous example, this request will be sent through the proxy
python -c "import httpx; httpx.get('http://example.com')"

# These requests will be sent directly, bypassing the proxy
python -c "import httpx; httpx.get('http://127.0.0.1:5000/my-api')"
python -c "import httpx; httpx.get('https://www.python-httpx.org')"
```
