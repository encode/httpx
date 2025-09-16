# Streams

Streams provide a minimal file-like interface for reading bytes from a data source. They are used as the abstraction for reading the body of a request or response.

The interfaces here are simplified versions of Python's standard I/O operations.

## Stream

The base `Stream` class. The core of the interface is a subset of Python's `io.IOBase`...

* `.read(size=-1)` - *(bytes)* Return the bytes from the data stream. If the `size` argument is omitted or negative then the entire stream will be read. If `size` is an positive integer then the call returns at most `size` bytes. A return value of `b''` indicates the end of the stream has been reached.
* `.write(self, data: bytes)` - *None* Write the given bytes to the data stream. May raise `NotImplmentedError` if this is not a writeable stream.
* `.close()` - Close the stream. Any further operations will raise a `ValueError`.

Additionally, the following property is also defined...

* `.size` - *(int or None)* Return an integer indicating the size of the stream, or `None` if the size is unknown. When working with HTTP this is used to either set a `Content-Length: <size>` header, or a `Content-Encoding: chunked` header.

The `Stream` interface and `ContentType` interface are related, with streams being used as the abstraction for the bytewise representation, and content types being used to encapsulate the parsed data structure.

For example, encoding some `JSON` data...

```python
>>> data = httpx.JSON({'name': 'zelda', 'score': '478'})
>>> stream = data.encode()
>>> stream.read()
b'{"name":"zelda","score":"478"}'
>>> stream.content_type
'application/json'
```

---

## ByteStream

A byte stream returning fixed byte content. Similar to Python's `io.BytesIO` class.

```python
>>> s = httpx.ByteStream(b'{"msg": "Hello, world!"}')
>>> s.read()
b'{"msg": "Hello, world!"}'
```

## FileStream

A byte stream returning content from a file.

The standard pattern for instantiating a `FileStream` is to use `File` as a context manager:

```python
>>> with httpx.File('upload.json') as s:
...     s.read()
b'{"msg": "Hello, world!"}'
```

## MultiPartStream

A byte stream returning multipart upload data.

The standard pattern for instantiating a `MultiPartStream` is to use `MultiPart` as a context manager:

```python
>>> files = {'avatar-upload': 'image.png'}
>>> with httpx.MultiPart(files=files) as s:
...     s.read()
# ...
```

## HTTPStream

A byte stream returning unparsed content from an HTTP request or response.

```python
>>> with httpx.Client() as cli:
...     r = cli.get('https://www.example.com/')
...     r.stream.read()
# ...
```

## GZipStream

...

---

<span class="link-prev">← [Content Types](content-types.md)</span>
<span class="link-next">[Connections](connections.md) →</span>
<span>&nbsp;</span>
