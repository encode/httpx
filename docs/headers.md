# Headers

The `Headers` class provides an immutable case-insensitive multidict interface for accessing HTTP headers.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> headers = httpx.Headers({"Accept": "*/*"})
>>> headers
<Headers {"Accept": "*/*"}>
>>> headers['accept']
'*/*'
```

```{ .python .ahttpx .hidden }
>>> headers = ahttpx.Headers({"Accept": "*/*"})
>>> headers
<Headers {"Accept": "*/*"}>
>>> headers['accept']
'*/*'
```

Header values should always be printable ASCII strings. Attempting to set invalid header name or value strings will raise a `ValueError`.

### Accessing headers

Headers are accessed using a standard dictionary style interface...

* `.get(key, default=None)` - *Return the value for a given key, or a default value. If multiple values for the key are present, only the first will be returned.*
* `.keys()` - *Return the unique keys of the headers. Each key will be a `str`.*
* `.values()` - *Return the values of the headers. Each value will be a `str`. If multiple values for a key are present, only the first will be returned.*
* `.items()` - *Return the key value pairs of the headers. Each item will be a two-tuple `(str, str)`. If multiple values for a key are present, only the first will be returned.*

The following methods are also available for accessing headers as a multidict...

* `.get_all(key, comma_delimited=False)` - *Return all the values for a given key. Returned as a list of zero or more `str` instances. If `comma_delimited` is set to `True` then any comma separated header values are split into a list of strings.*
* `.multi_items()` - *Return the key value pairs of the headers. Each item will be a two-tuple `(str, str)`. Repeated keys may occur.*
* `.multi_dict()` - *Return the headers as a dictionary, with each value being a list of one or more `str` instances.*

### Modifying headers

The following methods can be used to create modified header instances...

* `.copy_set(key, value)` - *Return a new `Headers` instances, setting a header. Eg. `headers = headers.copy_set("Connection": "close")`*.
* `.copy_setdefault(key, value)` - *Return a new `Headers` instances, setting a header if it does not yet exist. Eg. `headers = headers.copy_setdefault("Content-Type": "text/html")`*.
* `.copy_append(key, value, comma_delimited=False)` - *Return a new `Headers` instances, setting or appending a header. If `comma_delimited` is set to `True`, then the append will be handled using comma delimiting instead of creating a new header. Eg. `headers = headers.copy_append("Accept-Encoding", "gzip", comma_delimited=True)`*.
* `.copy_remove(key)` - *Return a new `Headers` instances, removing a header. Eg. `headers = headers.copy_remove("User-Agent")`*.
* `.copy_update(headers)` - *Return a new `Headers` instances, updating multiple headers. Eg. `headers = headers.copy_update({"Authorization": "top secret"})`*.

---

<span class="link-prev">← [URLs](urls.md)</span>
<span class="link-next">[Content Types](content-types.md) →</span>
<span>&nbsp;</span>