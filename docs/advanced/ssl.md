When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

### Enabling and disabling verification

By default httpx will verify HTTPS connections, and raise an error for invalid SSL cases...

```pycon
>>> httpx.get("https://expired.badssl.com/")
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)
```

You can configure the verification using `httpx.SSLContext()`.

```pycon
>>> ssl_context = httpx.SSLContext()
>>> ssl_context
SSLContext(verify=True)
>>> httpx.get("https://www.example.com", ssl_context=ssl_context)
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)
```

For example, you can use this to disable verification completely and allow insecure requests...

```pycon
>>> no_verify = httpx.SSLContext(verify=False)
>>> no_verify
SSLContext(verify=False)
>>> httpx.get("https://expired.badssl.com/", ssl_context=no_verify)
<Response [200 OK]>
```

### Configuring client instances

If you're using a `Client()` instance, then you should pass any SSL settings when instantiating the client.

```python
>>> ssl_context = httpx.SSLContext()
>>> client = httpx.Client(ssl_context=ssl_context)
```

The `client.get(...)` method and other request methods on a `Client` instance *do not* support changing the SSL settings on a per-request basis.

If you need different SSL settings in different cases you should use more that one client instance, with different settings on each. Each client will then be using an isolated connection pool with a specific fixed SSL configuration on all connections within that pool.

### Changing the verification defaults

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/).

The following all have the same behaviour...

Using the default SSL context.

```pycon
>>> client = httpx.Client()
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

Using the default SSL context, but specified explicitly.

```pycon
>>> default = httpx.SSLContext()
>>> client = httpx.Client(ssl_context=default)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

Using the default SSL context, with `verify=True` specified explicitly.

```pycon
>>> default = httpx.SSLContext(verify=True)
>>> client = httpx.Client(ssl_context=default)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

Using an SSL context, with `certifi.where()` explicitly specified.

```pycon
>>> default = httpx.SSLContext(verify=certifi.where())
>>> client = httpx.Client(ssl_context=default)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

For some advanced situations may require you to use a different set of certificates, either by specifying a PEM file:

```pycon
>>> custom_cafile = httpx.SSLContext(verify="path/to/certs.pem")
>>> client = httpx.Client(ssl_context=custom_cafile)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

Or by providing an certificate directory:

```pycon
>>> custom_capath = httpx.SSLContext(verify="path/to/certs")
>>> client = httpx.Client(ssl_context=custom_capath)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

These usages are equivelent to using [`.load_verify_locations()`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations) with either `cafile=...` or `capath=...`.

### Client side certificates

You can also specify a local cert to use as a client-side certificate, either a path to an SSL certificate file...

```pycon
>>> cert = "path/to/client.pem"
>>> ssl_context = httpx.SSLContext(cert=cert)
>>> httpx.get("https://example.org", ssl_context=ssl_context)
<Response [200 OK]>
```

Or two-tuple of (certificate file, key file)...

```pycon
>>> cert = ("path/to/client.pem", "path/to/client.key")
>>> ssl_context = httpx.SSLContext(cert=cert)
>>> httpx.get("https://example.org", ssl_context=ssl_context)
<Response [200 OK]>
```

Or a three-tuple of (certificate file, key file, password)...

```pycon
>>> cert = ("path/to/client.pem", "path/to/client.key", "password")
>>> ssl_context = httpx.SSLContext(cert=cert)
>>> httpx.get("https://example.org", ssl_context=ssl_context)
<Response [200 OK]>
```

These configurations are equivalent to using [`.load_cert_chain()`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain).

### Using alternate SSL contexts

You can also use an alternate `ssl.SSLContext` instances.

For example, [using the `truststore` package](https://truststore.readthedocs.io/)...

```python
import ssl
import truststore
import httpx

ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
client = httpx.Client(ssl_context=ssl_context)
```

Or working [directly with Python's standard library](https://docs.python.org/3/library/ssl.html)...

```python
import ssl
import httpx

ssl_context = ssl.create_default_context()
client = httpx.Client(ssl_context=ssl_context)
```

### Working with `SSL_CERT_FILE` and `SSL_CERT_DIR`

Unlike `requests`, the `httpx` package does not automatically pull in [the environment variables `SSL_CERT_FILE` or `SSL_CERT_DIR`](https://www.openssl.org/docs/manmaster/man3/SSL_CTX_set_default_verify_paths.html). If you want to use these they need to be enabled explicitly.

For example...

```python
# Use `SSL_CERT_FILE` or `SSL_CERT_DIR` if configured, otherwise use certifi.
verify = os.environ.get("SSL_CERT_FILE", os.environ.get("SSL_CERT_DIR", True))
ssl_context = httpx.SSLContext(verify=verify)
```

### Working with `SSLKEYLOGFILE`

This environment variable is used for [inspecing and debugging SSL](https://everything.curl.dev/usingcurl/tls/sslkeylogfile).

Unlike `requests` or the standard library [`ssl.create_default_context`](https://docs.python.org/3/library/ssl.html#ssl.create_default_context) the `httpx` package does not automatically configure an SSL context to use `SSLKEYLOGFILE`. If you want to use this it needs to be configured explicitly.

For example...

**example.py**:

```python
import os
import httpx

def create_client():
    # Setup our SSL context
    ssl_context = httpx.SSLContext()
    keylog_filename = os.environ.get("SSLKEYLOGFILE")
    if keylog_filename:
        ssl_context.keylog_filename = keylog_filename

    # Create a client instance
    return httpx.Client(ssl_context=ssl_context)

client = create_client()
client.get("https://google.com")
```

We can now enable SSL key logging...

```shell
$ # Run the above example with SSLKEYLOGFILE debugging enabled.
$ SSLKEYLOGFILE=test.log python example.py
$ # Inspect the TLS secrets log file.
$ cat test.log
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

### Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme](https://github.com/python-trio/trustme) to generate a pair of server key/cert files, and a client cert file.
2. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
3. Tell HTTPX to use the certificates stored in `client.pem`:

```pycon
>>> import httpx
>>> ssl_context = httpx.SSLContext(verify="/tmp/client.pem")
>>> r = httpx.get("https://localhost:8000", ssl_context=ssl_context)
>>> r
Response <200 OK>
```

