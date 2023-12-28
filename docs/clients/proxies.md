### ...

```pycon
>>> response = httpx.get(proxy="http://127.0.0.1:8080/")
...
```

```pycon
>>> client = httpx.Client(proxy="http://127.0.0.1:8080/")
>>> response = client.get("https://www.example.com/")
...
```

```pycon
>>> proxy = httpx.Proxy("http://127.0.0.1:8080/")
>>> client = httpx.Client(proxy=proxy)
>>> response = client.get("https://www.example.com/")
```

Proxy information can either be configured using a plain string representing the proxy URL, or using the `httpx.Proxy()` configuration object for more advanced control:

```python
def create_client():
    proxy = httpx.Proxy(
        "http://127.0.0.1:8080/",
        auth=("username", "password"),
        ssl_context=...,
        headers={...},
    )
    return httpx.Client(proxy=proxy)

...
```

### HTTP proxies

...

### HTTPS proxies

...

### Socks proxies

...
