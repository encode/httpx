# Content Types

Some HTTP requests including `POST`, `PUT` and `PATCH` can include content in the body of the request.

The most common content types for upload data are...

* HTML form submissions use the `application/x-www-form-urlencoded` content type.
* HTML form submissions including file uploads use the `multipart/form-data` content type.
* JSON data uses the `application/json` content type.

Content can be included directly in a request by using bytes or a byte iterator and setting the appropriate `Content-Type` header.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> headers = {'Content-Type': 'application/json'}
>>> content = json.dumps({"number": 123.5, "bool": [True, False], "text": "hello"})
>>> response = cli.put(url, headers=headers, content=content)
```

```{ .python .ahttpx .hidden }
>>> headers = {'Content-Type': 'application/json'}
>>> content = json.dumps({"number": 123.5, "bool": [True, False], "text": "hello"})
>>> response = await cli.put(url, headers=headers, content=content)
```

There are also several classes provided for setting the request content. These implement either the `Content` or `StreamingContent` API, and handle constructing the content and setting the relevant headers.

* `<Form {“email”: “heya@noodles.com”}>`
* `<Files {“upload”: File("README.md”)}>`
* `<File “README.md” [123MB]>`
* `<MultiPart {} {“upload”: File("README.md”)}>`
* `<JSON {"number": 123.5, "bool": [True, False], ...}>`

For example, sending a JSON request...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> data = httpx.JSON({"number": 123.5, "bool": [True, False], "text": "hello"})
>>> cli.post(url, content=data)
```

```{ .python .ahttpx .hidden }
>>> data = httpx.JSON({"number": 123.5, "bool": [True, False], "text": "hello"})
>>> await cli.post(url, content=data)
```

---

## Form

The `Form` class provides an immutable multi-dict for accessing HTML form data. This class implements the `Content` interface, allowing for HTML form uploads.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> form = httpx.Form({'name': '...'})
>>> form
...
>>> form['name']
...
>>> res = cli.post(url, content=form)
...
```

```{ .python .ahttpx .hidden }
>>> form = httpx.Form({'name': '...'})
>>> form
...
>>> form['name']
...
>>> res = await cli.post(url, content=form)
...
```

## Files

The `Files` class provides an immutable multi-dict for accessing HTML form file uploads. This class implements the `StreamingContent` interface, allowing for HTML form file uploads.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> files = httpx.Files({'upload': httpx.File('data.json')})
>>> files
...
>>> files['upload']
...
>>> res = cli.post(url, content=files)
...
```

```{ .python .ahttpx .hidden }
>>> files = httpx.Files({'upload': httpx.File('data.json')})
>>> files
...
>>> files['upload']
...
>>> res = await cli.post(url, content=files)
...
```

## MultiPart

The `MultiPart` class provides a wrapper for HTML form and files uploads. This class implements the `StreamingContent` interface, allowing for allowing for HTML form uploads including both data and file uploads.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> multipart = httpx.MultiPart(form={'name': '...'}, files={'avatar': httpx.File('image.png')})
>>> multipart.form['name']
...
>>> multipart.files['avatar']
...
>>> res = cli.post(url, content=multipart)
```

```{ .python .ahttpx .hidden }
>>> multipart = httpx.MultiPart(form={'name': '...'}, files={'avatar': httpx.File('image.png')})
>>> multipart.form['name']
...
>>> multipart.files['avatar']
...
>>> res = await cli.post(url, content=multipart)
```

## File

The `File` class provides a wrapper for file uploads, and is used for uploads instead of passing a file object directly.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> file = httpx.File('upload.json')
>>> cli.post(url, content=file)
```

```{ .python .ahttpx .hidden }
>>> file = httpx.File('upload.json')
>>> await cli.post(url, content=file)
```

## JSON

The `JSON` class provides a wrapper for JSON uploads. This class implements the `Content` interface, allowing for HTTP JSON uploads.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> data = httpx.JSON({...})
>>> cli.put(url, content=data)
```

```{ .python .ahttpx .hidden }
>>> data = httpx.JSON({...})
>>> await cli.put(url, content=data)
```

---

## Content

An interface for constructing HTTP content, along with relevant headers.

The following method must be implemented...

* `.encode()` - Returns an `httx.Stream` representing the encoded data.
* `.content_type()` - Returns a `str` indicating the content type.

---

<span class="link-prev">← [Headers](headers.md)</span>
<span class="link-next">[Streams](streams.md) →</span>
<span>&nbsp;</span>
