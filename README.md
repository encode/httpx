<p align="center">
  <img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/butterfly.png" alt='HTTPX'>
</p>

<p align="center"><em>HTTPX 1.0 — Design proposal.</em></p>

---

A complete HTTP framework for Python.

*Installation...*

```shell
$ pip install --pre httpx
```

*Making requests as a client...*

```python
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

*Serving responses as the server...*

```python
>>> def app(request):
...     content = httpx.HTML('<html><body>hello, world.</body></html>')
...     return httpx.Response(200, content=content)

>>> httpx.run(app)
Serving on http://127.0.0.1:8080/ (Press CTRL+C to quit)
```

---

# Documentation

The [HTTPX 1.0 design proposal](https://www.encode.io/httpnext/) is now available.

* [Quickstart](https://www.encode.io/httpnext/quickstart)
* [Clients](https://www.encode.io/httpnext/clients)
* [Servers](https://www.encode.io/httpnext/servers)
* [Requests](https://www.encode.io/httpnext/requests)
* [Responses](https://www.encode.io/httpnext/responses)
* [URLs](https://www.encode.io/httpnext/urls)
* [Headers](https://www.encode.io/httpnext/headers)
* [Content Types](https://www.encode.io/httpnext/content-types)
* [Connections](https://www.encode.io/httpnext/connections)
* [Parsers](https://www.encode.io/httpnext/parsers)
* [Network Backends](https://www.encode.io/httpnext/networking)

---

# Collaboration

We are not currently accepting unsolicted pull requests against the 1.0 pre-release branch.

We’re looking at creating paid opportunities for working on open source software *which are properly compensated, flexible & well balanced.*

If you're interested in a working on this project, please <a href="mailto:kim@encode.io">send an intro</a>.

---

<p align="center"><i>This provisional design work is <a href="https://github.com/encode/httpnext/blob/master/LICENSE.md">not currently licensed</a> for reuse.<br/>Designed & crafted with care.</i><br/>&mdash; 🦋 &mdash;</p>
