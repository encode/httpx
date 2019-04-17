# HTTPCore

A low-level async HTTP library.

## Proposed functionality

* Support for streaming requests and responses. (Done)
* Support for connection pooling. (Done)
* gzip, deflate, and brotli decoding. (Done)
* SSL verification. (Done)
* Proxy support. (Not done)
* HTTP/2 support. (Not done)
* Support *both* async and sync operations. (Sync will be lightweight shim on top of async. Not done.)

## Motivation

Some of the trickier remaining issues on `requests-async` such as request/response streaming, connection pooling, proxy support, would require a fully async variant of urllib3. I considered and started work on a straight port of `urllib3-async`, but having started to dive into it, my judgement is that a from-scratch implementation will be less overall work to achieve.

The intent is that this library could be the low-level implementation, that `requests-async` would then wrap up.

## Credit

* Some inspiration from the design-work of `urllib3`, but redone from scratch, and built as an async-first library.
* Dependant on the absolutely excellent `h11` package.
* Uses the `certifi` package for the default SSL verification.

## Usage

Making a request:

```python
import httpcore

http = httpcore.ConnectionPool()
response = await http.request('GET', 'http://example.com')
assert response.status_code == 200
assert response.body == b'Hello, world'
```

Top-level API:

```python
http = httpcore.ConnectionPool([ssl], [timeout], [limits])
response = await http.request(method, url, [headers], [body], [stream])
```

ConnectionPool as a context-manager:

```python
async with httpcore.ConnectionPool([ssl], [timeout], [limits]) as http:
    response = await http.request(method, url, [headers], [body], [stream])
```

Streaming responses:

```python
http = httpcore.ConnectionPool()
response = await http.request(method, url, stream=True)
async for part in response.stream():
    ...
```

## Building a Gateway Server

The level of abstraction fits in really well if you're just writing at
the raw ASGI level. Eg. Here's an how an ASGI gateway server looks against the
API, including streaming uploads and downloads...

```python
import httpcore


class GatewayServer:
    def __init__(self, base_url):
        self.base_url = base_url
        self.http = httpcore.ConnectionPool()

    async def __call__(self, scope, receive, send):
        assert scope['type'] == 'http'
        path = scope['path']
        query = scope['query_string']
        method = scope['method']
        headers = [
            (k, v) for (k, v) in scope['headers']
            if k not in (b'host', b'content-length', b'transfer-encoding')
        ]

        url = self.base_url + path
        if query:
            url += '?' + query.decode()

        initial_body, more_body = await self.initial_body(receive)
        if more_body:
            # Streaming request.
            body = self.stream_body(receive, initial_body)
        else:
            # Standard request.
            body = initial_body

        response = await self.http.request(
            method, url, headers=headers, body=body, stream=True
        )

        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': response.headers
        })
        data = b''
        async for next_data in response.stream():
            if data:
                await send({
                    'type': 'http.response.body',
                    'body': data,
                    'more_body': True
                })
            data = next_data
        await send({'type': 'http.response.body', 'body': data})

    async def initial_body(self, receive):
        """
        Pull the first body message off the 'receive' channel.
        Allows us to determine if we should use a streaming request or not.
        """
        message = await receive()
        body = message.get('body', b'')
        more_body = message.get('more_body', False)
        return (body, more_body)

    async def stream_body(self, receive, initial_body):
        """
        Async iterator returning bytes for the request body.
        """
        yield initial_body
        while True:
            message = await receive()
            yield message.get('body', b'')
            if not message.get('more_body', False):
                break


app = GatewayServer('http://example.org')
```

Run with...

```shell
uvicorn example:app
```
