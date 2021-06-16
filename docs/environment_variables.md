# Environment Variables

The HTTPX library can be configured via environment variables.
Environment variables are used by default. To ignore environment variables, `trust_env` has to be set `False`. There are two ways to set `trust_env` to disable environment variables:

* On the client via `httpx.Client(trust_env=False)`.
* Using the top-level API, such as `httpx.get("<url>", trust_env=False)`.

Here is a list of environment variables that HTTPX recognizes and what function they serve:

## `HTTPX_LOG_LEVEL`

Valid values: `debug`, `trace` (case-insensitive)

If set to `debug`, then HTTP requests will be logged to `stderr`. This is useful for general purpose reporting of network activity.

If set to `trace`, then low-level details about the execution of HTTP requests will be logged to `stderr`, in addition to debug log lines. This can help you debug issues and see what's exactly being sent over the wire and to which location.

Example:

```python
# test_script.py
import httpx

with httpx.Client() as client:
    r = client.get("https://google.com")
```

Debug output:

```console
$ HTTPX_LOG_LEVEL=debug python test_script.py
DEBUG [2019-11-06 19:11:24] httpx._client - HTTP Request: GET https://google.com "HTTP/1.1 301 Moved Permanently"
DEBUG [2019-11-06 19:11:24] httpx._client - HTTP Request: GET https://www.google.com/ "HTTP/1.1 200 OK"
```

Trace output:

```console
$ HTTPX_LOG_LEVEL=trace python test_script.py
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection_pool - acquire_connection origin=Origin(scheme='https' host='google.com' port=443)
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection_pool - new_connection connection=HTTPConnection(origin=Origin(scheme='https' host='google.com' port=443))
TRACE [2019-11-06 19:18:56] httpx._config - load_ssl_context verify=True cert=None trust_env=True http_versions=HTTPVersionConfig(['HTTP/1.1', 'HTTP/2'])
TRACE [2019-11-06 19:18:56] httpx._config - load_verify_locations cafile=/Users/florimond/Developer/python-projects/httpx/venv/lib/python3.8/site-packages/certifi/cacert.pem
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection - start_connect host='google.com' port=443 timeout=Timeout(timeout=5.0)
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection - connected http_version='HTTP/2'
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - send_headers stream_id=1 method='GET' target='/' headers=[(b':method', b'GET'), (b':authority', b'google.com'), (b':scheme', b'https'), (b':path', b'/'), (b'user-agent', b'python-httpx/0.7.6'), (b'accept', b'*/*'), (b'accept-encoding', b'gzip, deflate, br'), (b'connection', b'keep-alive')]
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - end_stream stream_id=1
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<RemoteSettingsChanged changed_settings:{ChangedSetting(setting=SettingCodes.MAX_CONCURRENT_STREAMS, original_value=None, new_value=100), ChangedSetting(setting=SettingCodes.INITIAL_WINDOW_SIZE, original_value=65535, new_value=1048576), ChangedSetting(setting=SettingCodes.MAX_HEADER_LIST_SIZE, original_value=None, new_value=16384)}>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<WindowUpdated stream_id:0, delta:983041>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<SettingsAcknowledged changed_settings:{}>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=1 event=<ResponseReceived stream_id:1, headers:[(b':status', b'301'), (b'location', b'https://www.google.com/'), (b'content-type', b'text/html; charset=UTF-8'), (b'date', b'Wed, 06 Nov 2019 18:18:56 GMT'), (b'expires', b'Fri, 06 Dec 2019 18:18:56 GMT'), (b'cache-control', b'public, max-age=2592000'), (b'server', b'gws'), (b'content-length', b'220'), (b'x-xss-protection', b'0'), (b'x-frame-options', b'SAMEORIGIN'), (b'alt-svc', b'quic=":443"; ma=2592000; v="46,43",h3-Q050=":443"; ma=2592000,h3-Q049=":443"; ma=2592000,h3-Q048=":443"; ma=2592000,h3-Q046=":443"; ma=2592000,h3-Q043=":443"; ma=2592000')]>
DEBUG [2019-11-06 19:18:56] httpx._client - HTTP Request: GET https://google.com "HTTP/2 301 Moved Permanently"
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection_pool - acquire_connection origin=Origin(scheme='https' host='www.google.com' port=443)
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection_pool - new_connection connection=HTTPConnection(origin=Origin(scheme='https' host='www.google.com' port=443))
TRACE [2019-11-06 19:18:56] httpx._config - load_ssl_context verify=True cert=None trust_env=True http_versions=HTTPVersionConfig(['HTTP/1.1', 'HTTP/2'])
TRACE [2019-11-06 19:18:56] httpx._config - load_verify_locations cafile=/Users/florimond/Developer/python-projects/httpx/venv/lib/python3.8/site-packages/certifi/cacert.pem
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection - start_connect host='www.google.com' port=443 timeout=Timeout(timeout=5.0)
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection - connected http_version='HTTP/2'
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - send_headers stream_id=1 method='GET' target='/' headers=[(b':method', b'GET'), (b':authority', b'www.google.com'), (b':scheme', b'https'), (b':path', b'/'), (b'user-agent', b'python-httpx/0.7.6'), (b'accept', b'*/*'), (b'accept-encoding', b'gzip, deflate, br'), (b'connection', b'keep-alive')]
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - end_stream stream_id=1
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<RemoteSettingsChanged changed_settings:{ChangedSetting(setting=SettingCodes.MAX_CONCURRENT_STREAMS, original_value=None, new_value=100), ChangedSetting(setting=SettingCodes.INITIAL_WINDOW_SIZE, original_value=65535, new_value=1048576), ChangedSetting(setting=SettingCodes.MAX_HEADER_LIST_SIZE, original_value=None, new_value=16384)}>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<WindowUpdated stream_id:0, delta:983041>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<SettingsAcknowledged changed_settings:{}>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=1 event=<ResponseReceived stream_id:1, headers:[(b':status', b'200'), (b'date', b'Wed, 06 Nov 2019 18:18:56 GMT'), (b'expires', b'-1'), (b'cache-control', b'private, max-age=0'), (b'content-type', b'text/html; charset=ISO-8859-1'), (b'p3p', b'CP="This is not a P3P policy! See g.co/p3phelp for more info."'), (b'content-encoding', b'gzip'), (b'server', b'gws'), (b'content-length', b'5073'), (b'x-xss-protection', b'0'), (b'x-frame-options', b'SAMEORIGIN'), (b'set-cookie', b'1P_JAR=2019-11-06-18; expires=Fri, 06-Dec-2019 18:18:56 GMT; path=/; domain=.google.com; SameSite=none'), (b'set-cookie', b'NID=190=m8G9qLxCz2_4HbZI02ON2HTJF4xTvOhoJiS57Hm-OJrNS2eY20LfXMR_u-mLjujeshW5-BTezI69OGpHksT4ZK2TCDsWeU0DF7AmDTjjXFOdj30eIUTpNq7r9aWRvI8UrqiwlIsLkE8Ee3t5PiIiVdSMUcji7dkavGlMUpkMXU8; expires=Thu, 07-May-2020 18:18:56 GMT; path=/; domain=.google.com; HttpOnly'), (b'alt-svc', b'quic=":443"; ma=2592000; v="46,43",h3-Q050=":443"; ma=2592000,h3-Q049=":443"; ma=2592000,h3-Q048=":443"; ma=2592000,h3-Q046=":443"; ma=2592000,h3-Q043=":443"; ma=2592000')]>
DEBUG [2019-11-06 19:18:56] httpx._client - HTTP Request: GET https://www.google.com/ "HTTP/2 200 OK"
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=1 event=<DataReceived stream_id:1, flow_controlled_length:5186, data:1f8b08000000000002ffc55af97adb4692ff3f4f>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=1 event=<DataReceived stream_id:1, flow_controlled_length:221, data:>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=1 event=<StreamEnded stream_id:1>
TRACE [2019-11-06 19:18:56] httpx._dispatch.http2 - receive_event stream_id=0 event=<PingReceived ping_data:0000000000000000>
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection_pool - release_connection connection=HTTPConnection(origin=Origin(scheme='https' host='www.google.com' port=443))
TRACE [2019-11-06 19:18:56] httpx._dispatch.connection - close_connection
```

## `SSLKEYLOGFILE`

Valid values: a filename

If this environment variable is set, TLS keys will be appended to the specified file, creating it if it doesn't exist, whenever key material is generated or received. The keylog file is designed for debugging purposes only.

Support for `SSLKEYLOGFILE` requires Python 3.8 and OpenSSL 1.1.1 or newer.

Example:

```python
# test_script.py
import httpx

with httpx.AsyncClient() as client:
    r = client.get("https://google.com")
```

```console
SSLKEYLOGFILE=test.log python test_script.py
cat test.log
# TLS secrets log file, generated by OpenSSL / Python
SERVER_HANDSHAKE_TRAFFIC_SECRET XXXX
EXPORTER_SECRET XXXX
SERVER_TRAFFIC_SECRET_0 XXXX
CLIENT_HANDSHAKE_TRAFFIC_SECRET XXXX
CLIENT_TRAFFIC_SECRET_0 XXXX
SERVER_HANDSHAKE_TRAFFIC_SECRET XXXX
EXPORTER_SECRET XXXX
SERVER_TRAFFIC_SECRET_0 XXXX
CLIENT_HANDSHAKE_TRAFFIC_SECRET XXXX
CLIENT_TRAFFIC_SECRET_0 XXXX
```

## `SSL_CERT_FILE`

Valid values: a filename

If this environment variable is set then HTTPX will load
CA certificate from the specified file instead of the default
location.

Example:

```console
SSL_CERT_FILE=/path/to/ca-certs/ca-bundle.crt python -c "import httpx; httpx.get('https://example.com')"
```

## `SSL_CERT_DIR`

Valid values: a directory following an [OpenSSL specific layout](https://www.openssl.org/docs/manmaster/man3/SSL_CTX_load_verify_locations.html).

If this environment variable is set and the directory follows an [OpenSSL specific layout](https://www.openssl.org/docs/manmaster/man3/SSL_CTX_load_verify_locations.html) (ie. you ran `c_rehash`) then HTTPX will load CA certificates from this directory instead of the default location.

Example:

```console
SSL_CERT_DIR=/path/to/ca-certs/ python -c "import httpx; httpx.get('https://example.com')"
```

## `NETRC`

Valid values: a filename

If this environment variable is set but auth parameter is not defined, HTTPX will add auth information stored in the .netrc file into the request's header. If you do not provide NETRC environment either, HTTPX will use default files. (~/.netrc, ~/_netrc)

Example:

```console
NETRC=/path/to/netrcfile/.my_netrc python -c "import httpx; httpx.get('https://example.com')"
```

## Proxies

The environment variables documented below are used as a convention by various HTTP tooling, including:

* [cURL](https://github.com/curl/curl/blob/master/docs/MANUAL.md#environment-variables)
* [requests](https://github.com/psf/requests/blob/master/docs/user/advanced.rst#proxies)

For more information on using proxies in HTTPX, see [HTTP Proxying](advanced.md#http-proxying).

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

