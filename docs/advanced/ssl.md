When making a request over HTTPS we need to verify the identity of the requested host. We rely on the [`truststore`](https://truststore.readthedocs.io/en/latest/) package to load the system certificates, ensuring that `httpx` has the same behaviour on SSL sites as your browser.

### SSL verification

By default httpx will verify HTTPS connections, and raise an error for invalid SSL cases...

```python
>>> httpx.get("https://expired.badssl.com/")
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997)
```

If you're confident that you want to visit a site with an invalid certificate you can disable SSL verification completely...

```python
>>> httpx.get("https://expired.badssl.com/", verify=False)
<Response [200 OK]>
```

### Custom SSL configurations

If you're using a `Client()` instance you can pass the `verify=<...>` configuration when instantiating the client.

```python
>>> client = httpx.Client(verify=True)
```

For more complex configurations you can pass an [SSL Context](https://docs.python.org/3/library/ssl.html) instance...

```python
import certifi
import httpx
import ssl
import certifi

# Use certifi for certificate validation, rather than the system truststore.
ctx = ssl.create_default_context(cafile=certifi.where())
client = httpx.Client(verify=ctx)
```

### Client side certificates

Client side certificates allow a remote server to verify the client. They tend to be used within private organizations to authenticate requests to remote servers.

You can specify client-side certificates, using the [`.load_cert_chain()`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain) API...

```python
ctx = ssl.create_default_context()
ctx.load_cert_chain(certfile="path/to/client.pem")  # Optionally also keyfile or password.
client = httpx.Client(verify=ctx)
```

### Working with `SSL_CERT_FILE` and `SSL_CERT_DIR`

Unlike `requests`, the `httpx` package does not automatically pull in [the environment variables `SSL_CERT_FILE` or `SSL_CERT_DIR`](https://www.openssl.org/docs/manmaster/man3/SSL_CTX_set_default_verify_paths.html). 

These environment variables shouldn't be necessary since they're obsoleted by `truststore`. They can be enabled if required like so...

```python
# Use `SSL_CERT_FILE` or `SSL_CERT_DIR` if configured.
# Otherwise default to certifi.
ctx = ssl.create_default_context(
    cafile=os.environ.get("SSL_CERT_FILE", certifi.where()),
    capath=os.environ.get("SSL_CERT_DIR"),
)
client = httpx.Client(verify=ctx)
```

### Making HTTPS requests to a local server

When making requests to local servers such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it...

1. Use [trustme](https://github.com/python-trio/trustme) to generate a pair of server key/cert files, and a client cert file.
2. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
3. Configure `httpx` to use the certificates stored in `client.pem`.

```python
ctx = ssl.create_default_context(cafile="client.pem")
client = httpx.Client(verify=ctx)
```
