When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

### Enabling and disabling verification

By default httpx will verify HTTPS connections, and raise an error for invalid SSL cases...

```pycon
>>> httpx.get("https://expired.badssl.com/")
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)
```

Verification is configured through [the SSL Context API](https://docs.python.org/3/library/ssl.html#ssl-contexts).

```pycon
>>> context = httpx.SSLContext()
>>> context
<SSLContext(verify=True)>
>>> httpx.get("https://www.example.com", ssl_context=context)
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)
```

You can use this to disable verification completely and allow insecure requests...

```pycon
>>> context = httpx.SSLContext(verify=False)
>>> context
<SSLContext(verify=False)>
>>> httpx.get("https://expired.badssl.com/", ssl_context=context)
<Response [200 OK]>
```

### Configuring client instances

If you're using a `Client()` instance you should pass any SSL context when instantiating the client.

```pycon
>>> context = httpx.SSLContext()
>>> client = httpx.Client(ssl_context=context)
```

The `client.get(...)` method and other request methods on a `Client` instance *do not* support changing the SSL settings on a per-request basis.

If you need different SSL settings in different cases you should use more than one client instance, with different settings on each. Each client will then be using an isolated connection pool with a specific fixed SSL configuration on all connections within that pool.

### Configuring certificate stores

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/).

You can load additional certificate verification using the [`.load_verify_locations()`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations) API:

```pycon
>>> context = httpx.SSLContext()
>>> context.load_verify_locations(cafile="path/to/certs.pem")
>>> client = httpx.Client(ssl_context=context)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

Or by providing an certificate directory:

```pycon
>>> context = httpx.SSLContext()
>>> context.load_verify_locations(capath="path/to/certs")
>>> client = httpx.Client(ssl_context=context)
>>> client.get("https://www.example.com")
<Response [200 OK]>
```

### Client side certificates

You can also specify a local cert to use as a client-side certificate, using the [`.load_cert_chain()`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain) API:

```pycon
>>> context = httpx.SSLContext()
>>> context.load_cert_chain(certfile="path/to/client.pem")
>>> httpx.get("https://example.org", ssl_context=ssl_context)
<Response [200 OK]>
```

Or including a keyfile...

```pycon
>>> context = httpx.SSLContext()
>>> context.load_cert_chain(
        certfile="path/to/client.pem",
        keyfile="path/to/client.key"
    )
>>> httpx.get("https://example.org", ssl_context=context)
<Response [200 OK]>
```

Or including a keyfile and password...

```pycon
>>> context = httpx.SSLContext(cert=cert)
>>> context = httpx.SSLContext()
>>> context.load_cert_chain(
        certfile="path/to/client.pem",
        keyfile="path/to/client.key"
        password="password"
    )
>>> httpx.get("https://example.org", ssl_context=context)
<Response [200 OK]>
```

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
context = httpx.SSLContext()

# Use `SSL_CERT_FILE` or `SSL_CERT_DIR` if configured.
if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
    context.load_verify_locations(
        cafile=os.environ.get("SSL_CERT_FILE"),
        capath=os.environ.get("SSL_CERT_DIR"),
    )
```

## `SSLKEYLOGFILE`

Valid values: a filename

If this environment variable is set, TLS keys will be appended to the specified file, creating it if it doesn't exist, whenever key material is generated or received. The keylog file is designed for debugging purposes only.

Support for `SSLKEYLOGFILE` requires Python 3.8 and OpenSSL 1.1.1 or newer.

Example:

```python
# test_script.py
import httpx

with httpx.Client() as client:
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

### Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme](https://github.com/python-trio/trustme) to generate a pair of server key/cert files, and a client cert file.
2. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
3. Tell HTTPX to use the certificates stored in `client.pem`:

```pycon
>>> import httpx
>>> context = httpx.SSLContext()
>>> context.load_verify_locations(cafile="/tmp/client.pem")
>>> r = httpx.get("https://localhost:8000", ssl_context=context)
>>> r
Response <200 OK>
```
