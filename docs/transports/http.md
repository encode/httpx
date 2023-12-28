# The default transport

The default transport uses [the `httpcore` package](https://www.encode.io/httpcore/) to send HTTP requests.

...

```pycon
>>> transport = httpx.HTTPTransport()
>>> client = httpx.Client(transport=transport)
>>> response = client.get("https://www.example.com/)
```

## SSL context

```python
def create_client():
    ssl_context = httpx.SSLContext(...)
    transport = httpx.HTTPTransport(ssl_context=ssl_context)
    return httpx.Client(transport=transport)
```

## Proxies

```python
def create_client():
    proxy = httpx.Proxy(...)
    transport = httpx.HTTPTransport(proxy=proxy)
    return httpx.Client(transport=transport)
```

## HTTP version

```python
def create_client():
    http_version = httpx.HTTPVersion(...)
    transport = httpx.HTTPTransport(http_version=http_version)
    return httpx.Client(transport=transport)
```

## Resource limits

```python
def create_client():
    limits = httpx.Limits(...)
    transport = httpx.HTTPTransport(limits=limits)
    return httpx.Client(transport=transport)
```

## Network options

```python
def create_client():
    network_options = httpx.NetworkOptions(...)
    transport = httpx.HTTPTransport(network_options=network_options)
    return httpx.Client(transport=transport)
```
