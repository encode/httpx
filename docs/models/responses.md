# Response content

## Binary content

The simplest way to access the body of an HTTP response is using the `.content` property, which returns `bytes`.

```pycon
>>> response = httpx.get("https://www.example.com/")
>>> response.content
b'...'
```

## Text content

If you're accessing textual content such as HTML documents use the `.text` property, which handles decoding the byte content into a `str`.

```pycon
>>> response = httpx.get("https://www.example.com/")
>>> response.text
'...'
```

### Using the default encoding

...

### Using an explict encoding

...

### Using charset autodetection

...

## JSON data

For API responses returning JSON data, use the `.json()` method.

```python
>>> response = httpx.get("https://httpbin.org/json")
>>> print(response.json())
{'slideshow': {'author': 'Yours Truly', 'date': 'date of publication', 'slides': [{'title': 'Wake up to WonderWidgets!', 'type': 'all'}, {'items': ['Why <em>WonderWidgets</em> are great', 'Who <em>buys</em> WonderWidgets'], 'title': 'Overview', 'type': 'all'}], 'title': 'Sample Slide Show'}}
```

Responses that are not JSON data may raise a `json.decoder.JSONDecodeError` exception.

## Streaming responses

### Iterating the content

* `iter_lines()`
* `iter_text()`
* `iter_bytes()`
* `iter_raw()`

### Reading to completion

* `.read()`
* `.close()`

## Content Encodings

...