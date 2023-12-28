# Mount points

```python
transport = httpx.Mounts({
    "http://": httpx.HTTPTransport(proxy="127.0.0.1:8080"),
    "https://": httpx.HTTPTransport(),
})
with httpx.Client(transport=transport) as client:
    ...
```

```python
>>> proxies = httpx.get_env_proxies()
>>> print(proxies)
...
```

```python
transport = httpx.Mounts({
    key: httpx.HTTPTransport(proxy=value)
    for key, value in httpx.get_env_proxies().items()
})
```
