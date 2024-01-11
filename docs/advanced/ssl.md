When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

## Changing the verification defaults

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/). This is what you want in most cases, even though some advanced situations may require you to use a different set of certificates.

If you'd like to use a custom CA bundle, you can use the `verify` parameter.

```python
import httpx

r = httpx.get("https://example.org", verify="path/to/client.pem")
```

Alternatively, you can pass a standard library `ssl.SSLContext`.

```pycon
>>> import ssl
>>> import httpx
>>> context = ssl.create_default_context()
>>> context.load_verify_locations(cafile="/tmp/client.pem")
>>> httpx.get('https://example.org', verify=context)
<Response [200 OK]>
```

We also include a helper function for creating properly configured `SSLContext` instances.

```pycon
>>> context = httpx.create_ssl_context()
```

The `create_ssl_context` function accepts the same set of SSL configuration arguments
(`trust_env`, `verify`, `cert` and `http2` arguments)
as `httpx.Client` or `httpx.AsyncClient`

```pycon
>>> import httpx
>>> context = httpx.create_ssl_context(verify="/tmp/client.pem")
>>> httpx.get('https://example.org', verify=context)
<Response [200 OK]>
```

Or you can also disable the SSL verification entirely, which is _not_ recommended.

```python
import httpx

r = httpx.get("https://example.org", verify=False)
```

## SSL configuration on client instances

If you're using a `Client()` instance, then you should pass any SSL settings when instantiating the client.

```python
client = httpx.Client(verify=False)
```

The `client.get(...)` method and other request methods *do not* support changing the SSL settings on a per-request basis. If you need different SSL settings in different cases you should use more that one client instance, with different settings on each. Each client will then be using an isolated connection pool with a specific fixed SSL configuration on all connections within that pool.

## Client Side Certificates

You can also specify a local cert to use as a client-side certificate, either a path to an SSL certificate file, or two-tuple of (certificate file, key file), or a three-tuple of (certificate file, key file, password)

```python
cert = "path/to/client.pem"
client = httpx.Client(cert=cert)
response = client.get("https://example.org")
```

Alternatively...

```python
cert = ("path/to/client.pem", "path/to/client.key")
client = httpx.Client(cert=cert)
response = client.get("https://example.org")
```

Or...

```python
cert = ("path/to/client.pem", "path/to/client.key", "password")
client = httpx.Client(cert=cert)
response = client.get("https://example.org")
```

## Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme](https://github.com/python-trio/trustme) to generate a pair of server key/cert files, and a client cert file.
1. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
1. Tell HTTPX to use the certificates stored in `client.pem`:

```python
client = httpx.Client(verify="/tmp/client.pem")
response = client.get("https://localhost:8000")
```
