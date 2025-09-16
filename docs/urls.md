# URLs

The `URL` class handles URL validation and parsing.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> url = httpx.URL('https://www.example.com/')
>>> url
<URL 'https://www.example.com/'>
```

```{ .python .ahttpx .hidden }
>>> url = ahttpx.URL('https://www.example.com/')
>>> url
<URL 'https://www.example.com/'>
```

URL components are normalised, following the same rules as internet browsers.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> url = httpx.URL('https://www.EXAMPLE.com:443/path/../main')
>>> url
<URL 'https://www.example.com/main'>
```

```{ .python .ahttpx .hidden }
>>> url = ahttpx.URL('https://www.EXAMPLE.com:443/path/../main')
>>> url
<URL 'https://www.example.com/main'>
```

Both absolute and relative URLs are valid.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> url = httpx.URL('/README.md')
>>> url
<URL '/README.md'>
```

```{ .python .ahttpx .hidden }
>>> url = ahttpx.URL('/README.md')
>>> url
<URL '/README.md'>
```

Coercing a URL to a `str` will always result in a printable ASCII string.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> url = httpx.URL('https://example.com/path to here?search=🦋')
>>> str(url)
'https://example.com/path%20to%20here?search=%F0%9F%A6%8B'
```

```{ .python .ahttpx .hidden }
>>> url = ahttpx.URL('https://example.com/path to here?search=🦋')
>>> str(url)
'https://example.com/path%20to%20here?search=%F0%9F%A6%8B'
```

### URL components

The following properties are available for accessing the component parts of a URL.

* `.scheme` - *str. ASCII. Normalised to lowercase.*
* `.userinfo` - *str. ASCII. URL encoded.*
* `.username` - *str. Unicode.*
* `.password` - *str. Unicode.*
* `.host` - *str. ASCII. IDNA encoded.*
* `.port` - *int or None. Scheme default ports are normalised to None.*
* `.authority` - *str. ASCII. IDNA encoded. Eg. "example.com", "example.com:1337", "xn--p1ai".*
* `.path` - *str. Unicode.*
* `.query` - *str. ASCII. URL encoded.*
* `.target` - *str. ASCII. URL encoded.*
* `.fragment` - *str. ASCII. URL encoded.*

A parsed representation of the query parameters is accessible with the `.params` property.

* `.params` - [`QueryParams`](#query-parameters)

URLs can be instantiated from their components...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> httpx.URL(scheme="https", host="example.com", path="/")
<URL 'https://example.com/'>
```

```{ .python .ahttpx .hidden }
>>> ahttpx.URL(scheme="https", host="example.com", path="/")
<URL 'https://example.com/'>
```

Or using both the string form and query parameters...

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> httpx.URL("https://example.com/", params={"search": "some text"})
<URL 'https://example.com/?search=some+text'>
```

```{ .python .ahttpx .hidden }
>>> ahttpx.URL("https://example.com/", params={"search": "some text"})
<URL 'https://example.com/?search=some+text'>
```

### Modifying URLs

Instances of `URL` are immutable, meaning their value cannot be changed. Instead new modified instances may be created.

* `.copy_with(**components)` - *Return a new URL, updating one or more components. Eg. `url = url.copy_with(scheme="https")`*.
* `.copy_set_param(key, value)` - *Return a new URL, setting a query parameter. Eg. `url = url.copy_set_param("sort_by", "price")`*.
* `.copy_append_param(key, value)` - *Return a new URL, setting or appending a query parameter. Eg. `url = url.copy_append_param("tag", "sale")`*.
* `.copy_remove_param(key)` - *Return a new URL, removing a query parameter. Eg. `url = url.copy_remove_param("max_price")`*.
* `.copy_update_params(params)` - *Return a new URL, updating the query parameters. Eg. `url = url.copy_update_params({"color_scheme": "dark"})`*. 
* `.join(url)` - *Return a new URL, given this URL as the base and another URL as the target. Eg. `url = url.join("../navigation")`*.

---

## Query Parameters

The `QueryParams` class provides an immutable multi-dict for accessing URL query parameters.

They can be instantiated from a dictionary.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = httpx.QueryParams({"color": "black", "size": "medium"})
>>> params
<QueryParams 'color=black&size=medium'>
```

```{ .python .ahttpx .hidden }
>>> params = ahttpx.QueryParams({"color": "black", "size": "medium"})
>>> params
<QueryParams 'color=black&size=medium'>
```

Multiple values for a single key are valid.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = httpx.QueryParams({"filter": ["60GHz", "75GHz", "100GHz"]})
>>> params
<QueryParams 'filter=60GHz&filter=75GHz&filter=100GHz'>
```

```{ .python .ahttpx .hidden }
>>> params = ahttpx.QueryParams({"filter": ["60GHz", "75GHz", "100GHz"]})
>>> params
<QueryParams 'filter=60GHz&filter=75GHz&filter=100GHz'>
```

They can also be instantiated directly from a query string.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = httpx.QueryParams("color=black&size=medium")
>>> params
<QueryParams 'color=black&size=medium'>
```

```{ .python .ahttpx .hidden }
>>> params = ahttpx.QueryParams("color=black&size=medium")
>>> params
<QueryParams 'color=black&size=medium'>
```

Keys and values are always represented as strings.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = httpx.QueryParams("sort_by=published&author=natalie")
>>> params["sort_by"]
'published'
```

```{ .python .ahttpx .hidden }
>>> params = ahttpx.QueryParams("sort_by=published&author=natalie")
>>> params["sort_by"]
'published'
```

When coercing query parameters to strings you'll see the same escaping behavior as HTML form submissions. The result will always be a printable ASCII string.

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
>>> params = httpx.QueryParams({"email": "user@example.com", "search": "How HTTP works!"})
>>> str(params)
'email=user%40example.com&search=How+HTTP+works%21'
```

```{ .python .ahttpx .hidden }
>>> params = ahttpx.QueryParams({"email": "user@example.com", "search": "How HTTP works!"})
>>> str(params)
'email=user%40example.com&search=How+HTTP+works%21'
```

### Accessing query parameters

Query parameters are accessed using a standard dictionary style interface...

* `.get(key, default=None)` - *Return the value for a given key, or a default value. If multiple values for the key are present, only the first will be returned.*
* `.keys()` - *Return the unique keys of the query parameters. Each key will be a `str` instance.*
* `.values()` - *Return the values of the query parameters. Each value will be a list of one or more `str` instances.*
* `.items()` - *Return the key value pairs of the query parameters. Each item will be a two-tuple including a `str` instance as the key, and a list of one or more `str` instances as the value.*

The following methods are also available for accessing query parameters as a multidict...

* `.get_all(key)` - *Return all the values for a given key. Returned as a list of zero or more `str` instances.*
* `.multi_items()` - *Return the key value pairs of the query parameters. Each item will be a two-tuple `(str, str)`. Repeated keys may occur.*
* `.multi_dict()` - *Return the query parameters as a dictionary, with each value being a list of one or more `str` instances.*

### Modifying query parameters

The following methods can be used to create modified query parameter instances...

* `.copy_set(key, value)`
* `.copy_append(key, value)`
* `.copy_remove(key)`
* `.copy_update(params)`

---

<span class="link-prev">← [Responses](responses.md)</span>
<span class="link-next">[Headers](headers.md) →</span>
<span>&nbsp;</span>