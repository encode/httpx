# URLs

URLs are instantiated using plain strings.

```python
>>> url = httpx.URL('https://www.example.com/')
>>> url
URL('https://www.example.com/')
```

They can be coerced back into a plain string representation.

```python
>>> url = httpx.URL('https://www.example.com/')
>>> str(url)
'https://www.example.com/'
```

Using a URL in a string context will result in the plain string representation.

```python
>>> url = httpx.URL('https://www.example.com/')
>>> print(url)
https://www.example.com/
```

### URL components

The components that make up the URL are available as attributes on the `URL`.

* `.scheme` - The URL scheme such as `"http"` or `"https"`. Normalised to lowercase.
* `.host` - The URL host as a string such as `"www.example.com"` or `"127.0.0.1"`. Normlised to lowercase.
* `.port` - The port as an integer, or `None`. May be normalised to `None` if the default port for a scheme is provided.
* `.path` - The URL path as a unicode string, such as `/path`. Paths with `.` or `..` segments are normalised. URL escaping is applied.
* `.query` - The URL query as a unicode string, such as `search=for%20answers`. URL escaping is not applied. You'll typically want to access this component via the `.params` interface instead.
* `.fragment` - The URL fragment portion, as used in HTML anchors. This component is for client side information only, and is not used in outgoing HTTP requests.

There are two components that are represented with a byte representation, which appear directly as they are used in outgoing HTTP requests.

* `.netloc` - The host and port portion combined as used in the HTTP request `Host` header, such as `b"www.example.com:123"`.
* `.target` - The URL-escaped path and query strings, such as `b"/path?search=for%20answers"`.

### Query components

The `.query` component of the URL is also accessible via a multi-dict interface, allowing the query values to be inspected.

* `.params` - The parsed `httpx.QueryParams` object.

### Username and password components

URLs can also include `username` and `password` components. This is occasionally used for including basic authentication directly in a URL string, or for including authentication information in proxy URLs.

* `.username` - The `username` portion of a URL as a unicode string.
* `.password` - The `password` portion of a URL as a unicode string.

When including a username and password into a URL, unsafe characters should be encoded with URL escaping. These components will be normalised into their safe forms in the URL string if required.

```python
>>> url = httpx.URL("http://user@gmail.com:secret password@example.com/")
>>> url.username
"user@gmail.com"
>>> url.password
"secret password"
```

**TODO**: note representation and [secure].
**TODO**: `.userinfo`

### Absolute and relative URLs

The URL API allows you to deal with either absolute or relative URLs.

```python
>>> url = httpx.URL("https://www.example.com/absolutely")
>>> url.path
"/absolutely"
>>> url = httpx.URL("../path?search=for%20answers")
>>> url.path
"../path"
>>> url.query
"search=for%20answers"
```

Absolute URLs will always have any leading `.` or `..` segments normalised away.

### Instantiating with components

URLs can also be instantiated using their component parts.

```python
>>> url = httpx.URL(scheme="https", host="www.example.com", path="/")
>>> print(url)
https://www.example.com/
```

Or using combination of the URL string and component parts.

```python
>>> url = httpx.URL("https://www.example.com/", params={"search": "user@gmail.com"})
>>> print(url)
https://www.example.com/?search=user%40gmail.com
```

```python
>>> url = httpx.URL("https://www.example.com/", username="user@gmail.com", password="top secret")
>>> print(url)
https://user%40gmail.com:top%20secret@www.example.com/
```

**TODO**: Obscure in both `__str__` and `__repr__`.

### URL validation

Invalid URLs will raise an `httpx.InvalidURL` exception.

```python
>>> url = httpx.URL("https://0.0.0.999")
Traceback (most recent call last):
  File "/Users/tomchristie/GitHub/encode/httpx/httpx/_urlparse.py", line 297, in encode_host
    ipaddress.IPv4Address(host)
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/ipaddress.py", line 1305, in __init__
    self._ip = self._ip_int_from_string(addr_str)
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/ipaddress.py", line 1197, in _ip_int_from_string
    raise AddressValueError("%s in %r" % (exc, ip_str)) from None
ipaddress.AddressValueError: Octet 999 (> 255) not permitted in '0.0.0.999'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/tomchristie/GitHub/encode/httpx/httpx/_urls.py", line 115, in __init__
    self._uri_reference = urlparse(url, **kwargs)
  File "/Users/tomchristie/GitHub/encode/httpx/httpx/_urlparse.py", line 245, in urlparse
    parsed_host: str = encode_host(host)
  File "/Users/tomchristie/GitHub/encode/httpx/httpx/_urlparse.py", line 299, in encode_host
    raise InvalidURL(f"Invalid IPv4 address: {host!r}")
httpx.InvalidURL: Invalid IPv4 address: '0.0.0.999'
```

**TODO**: Clean up this traceback case.

### URL normalisation

...

### URL manipulation

* `.join()`
* `.copy_with(...)`

### Query parameters

**Discuss `.query` and `.params`**

You can work with query parameters directly, using `httpx.QueryParams`.

```python
>>> httpx.QueryParams("a=123")
```


```python
>>> params = httpx.QueryParams({"a": "123"})
```

**Discuss multi-value**

**Discuss allowable representations**

**TODO**: explain character escaping with plain strings, and `params={}`.

### Unicode characters in URLs

...

### IDNA hostnames

...

### Further reading

**TODO** Discuss why we're not using `urllib.parse`, etc.etc.

https://docs.python.org/3/library/urllib.parse.html#module-urllib.parse

For more information on handling URLs see [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986) and the [URL living standard](https://url.spec.whatwg.org/).

Other python packages for URL handling include:

* [rfc3986](https://github.com/python-hyper/rfc3986)
* [yarl](https://github.com/aio-libs/yarl/)
* [furl](https://github.com/gruns/furl)


https://en.wikipedia.org/wiki/URL
https://developer.mozilla.org/en-US/docs/Learn/Common_questions/Web_mechanics/What_is_a_URL