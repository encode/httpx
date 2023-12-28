# Custom transports

```python
class DebuggingTransport(httpx.BaseTransport):
    def __init__(self, transport=None):
        if transport is None:
            transport = httpx.HTTPTransport()
        self.transport = transport

    def handle_request(self, request):
        print(f">>> {request}")
        response = self.transport.handle_request(request)
        print(f"<<< {response}")


def create_client():
    transport = DebuggingTransport()
    return httpx.Client(transport=transport)


client = create_client()
response = client.get("https://www.example.com/")
```
