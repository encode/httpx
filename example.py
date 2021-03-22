# import contextlib
# import httpx
#
#
# class HTTPTransport:
#     @contextlib.contextmanager
#     def request(self, method, url, headers, stream, ext):
#         yield 200, {}, [], {}
#
#     def close(self):
#         pass
#
# c = httpx.Client(transport=HTTPTransport())
# r = c.get('https://www.example.org/')
# print(r)

import json
import httpcore


class HelloWorldTransport(httpcore.SyncHTTPTransport):
    """
    A mock transport that always returns a JSON "Hello, world!" response.
    """

    def request(self, method, url, headers=None, stream=None, ext=None):
        message = {"text": "Hello, world!"}
        content = json.dumps(message).encode("utf-8")
        stream = [content]
        headers = [(b"content-type", b"application/json")]
        ext = {"http_version": b"HTTP/1.1"}
        return 200, headers, stream, ext


import httpx
client = httpx.Client(transport=HelloWorldTransport())
response = client.get("https://example.org/")
print(response.json())
