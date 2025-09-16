# Servers

The HTTP server provides a simple request/response API.
This gives you a lightweight way to build web applications or APIs.

### `serve_http(endpoint)`

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> website = """
...     <html>
...         <head>
...             <style>
...                 body {
...                     font-family: courier;
...                     text-align: center;
...                     padding: 3rem;
...                     background: #111;
...                     color: #ddd;
...                     font-size: 3rem;
...                 }
...             </style>
...         </head>
...         <body>
...             <div>hello, world</div>
...         </body>
...     </html>
... """

>>> def hello_world(request):
...     content = httpx.HTML(website)
...     return httpx.Response(200, content=content)

>>> with httpx.serve_http(hello_world) as server:
...     print(f"Serving on {server.url} (Press CTRL+C to quit)")
...     server.wait()
Serving on http://127.0.0.1:8080/ (Press CTRL+C to quit)
```

```{ .python .ahttpx .hidden }
>>> import httpx

>>> website = """
...     <html>
...         <head>
...             <style>
...                 body {
...                     font-family: courier;
...                     text-align: center;
...                     padding: 3rem;
...                     background: #111;
...                     color: #ddd;
...                     font-size: 3rem;
...                 }
...             </style>
...         </head>
...         <body>
...             <div>hello, world</div>
...         </body>
...     </html>
... """

>>> async def hello_world(request):
...     if request.path != '/':
...         content = httpx.Text("Not found")
...         return httpx.Response(404, content=content)
...     content = httpx.HTML(website)
...     return httpx.Response(200, content=content)

>>> async with httpx.serve_http(hello_world) as server:
...     print(f"Serving on {server.url} (Press CTRL+C to quit)")
...     await server.wait()
Serving on http://127.0.0.1:8080/ (Press CTRL+C to quit)
```

---

*Docs in progress...*

---

<span class="link-prev">← [Clients](clients.md)</span>
<span class="link-next">[Requests](requests.md) →</span>
<span>&nbsp;</span>
