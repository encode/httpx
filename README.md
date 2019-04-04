# HTTPCore

```python
import httpcore

response = await httpcore.request('GET', 'http://example.com')
assert response.status_code == 200
assert response.body == b'Hello, world'
```

Top-level API...

```python
response = await httpcore.request(method, url, [headers], [body], [stream])
```

Explicit PoolManager...

```python
async with httpcore.PoolManager([ssl], [timeout], [limits]) as pool:
    response = await pool.request(method, url, [headers], [body], [stream])
```

Streaming...

```python
response = await httpcore.request(method, url, stream=True)
async for part in response.stream():
    ...
```

The level of abstraction fits in really well if you're just writing at
the raw ASGI level. Eg. Here's an how an ASGI gateway server looks against the
API, including streaming uploads and downloads...

```python
import httpcore


class GatewayServer:
    def __init__(self, base_url):
        self.base_url = base_url
        self.pool = httpcore.PoolManager()

    async def __call__(self, scope, receive, send):
        assert scope['type'] == 'http'
        path = scope['path']
        query = scope['query_string']
        method = scope['method']
        headers = scope['headers']

        url = self.base_url + path
        if query:
            url += '?' + query.decode()

        async def body():
            nonlocal receive

            while True:
                message = await receive()
                yield message.get('body', b'')
                if not message.get('more_body', False):
                    break

        response = await self.pool.request(
            method, url, headers=headers, body=body, stream=True
        )

        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': response.headers
        })
        async for data in response.stream():
            await send({
                'type': 'http.response.body',
                'body': data,
                'more_body': True
            })
        await send({'type': 'http.response.body'})


app = GatewayServer('http://example.org')
```

Run with...

```shell
uvicorn example:app
```
