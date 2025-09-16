<p align="center">
  <img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/butterfly.png" alt='HTTPX'>
</p>

<p align="center"><em>HTTPX 1.0 — Prelease.</em></p>

---

A complete HTTP toolkit for Python. Supporting both client & server, and available in either sync or async flavors.

---

*Installation...*

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .shell .httpx }
$ pip install --pre httpx
```

```{ .shell .ahttpx .hidden }
$ pip install --pre ahttpx
```

*Making requests as a client...*

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> import httpx

>>> r = httpx.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

```{ .python .ahttpx .hidden }
>>> import ahttpx

>>> r = await ahttpx.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

*Serving responses as the server...*

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> import httpx

>>> def app(request):
...     content = httpx.HTML('<html><body>hello, world.</body></html>')
...     return httpx.Response(200, content=content)

>>> httpx.run(app)
Serving on http://127.0.0.1:8080/ (Press CTRL+C to quit)
```

```{ .python .ahttpx .hidden }
>>> import ahttpx

>>> async def app(request):
...     content = httpx.HTML('<html><body>hello, world.</body></html>')
...     return httpx.Response(200, content=content)

>>> await httpx.run(app)
Serving on http://127.0.0.1:8080/ (Press CTRL+C to quit)
```

---

# Documentation

* [Quickstart](quickstart.md)
* [Clients](clients.md)
* [Servers](servers.md)
* [Requests](requests.md)
* [Responses](responses.md)
* [URLs](urls.md)
* [Headers](headers.md)
* [Content Types](content-types.md)
* [Streams](streams.md)
* [Connections](connections.md)
* [Parsers](parsers.md)
* [Network Backends](networking.md)

---

# Collaboration

The repository for this project is currently private.

We’re looking at creating paid opportunities for working on open source software *which are properly compensated, flexible & well balanced.*

If you're interested in a position working on this project, please send an intro: *kim&#x40;encode.io*

---

<p align="center"><i>This design work is <a href="https://www.encode.io/httpnext/about">not yet licensed</a> for reuse.</i><br/>&mdash; 🦋 &mdash;</p>
