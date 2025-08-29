# Query parameters (advanced)

HTTPX supports basic query strings via the `params` argument on request methods. By default, HTTPX handles flat key–value pairs and lists (repeating the key for each value), which covers most simple use cases. However, some APIs expect **nested/structured** query parameters (e.g. `a[b][c]=d`, lists of objects, duplicate keys, comma formats, etc.). For these cases, you can pair HTTPX with the third‑party package [**`qs_codec`**](https://pypi.org/project/qs-codec/) to encode and decode complex query strings.

`qs_codec` is a faithful Python port of Node.js’s widely used [`qs`](https://www.npmjs.com/package/qs) library. It has **zero external dependencies** and is thoroughly tested. With it, you can round‑trip nested dictionaries and lists to/from query strings, choose list formats, and control percent‑encoding semantics.

> Install with: `pip install qs-codec`

## Using `qs_codec` for complex query parameters

`qs_codec` provides simple `encode` and `decode` functions.

```python
import qs_codec as qs

# Encode a nested dict into a query string
payload = {"foo": {"bar": {"baz": "qux"}}}
query = qs.encode(payload)  # RFC 3986 percent-encoding by default
print(query)
# -> "foo%5Bbar%5D%5Bbaz%5D=qux"  (i.e. foo[bar][baz]=qux)

# Decode a query string back into Python data
round_tripped = qs.decode("foo[bar][baz]=qux")
print(round_tripped)
# -> {'foo': {'bar': {'baz': 'qux'}}}
```

Lists are supported, with configurable styles:

```python
# Default: indices (a[0]=x&a[1]=y)
qs.encode({"tags": ["httpx", "python"]})
# -> "tags%5B0%5D=httpx&tags%5B1%5D=python"

# Repeated keys (a=x&a=y)
qs.encode(
    {"tags": ["httpx", "python"]},
    qs.EncodeOptions(list_format=qs.ListFormat.REPEAT)
)
# -> "tags=httpx&tags=python"
```

You can also parse combined/duplicate keys into lists, and choose strategies such as combine/first/last when merging values.

### Space encoding modes

By default `qs_codec` uses RFC 3986 (space ⇒ `%20`). If you need `+` (RFC 1738) for legacy backends:

```python
qs.encode({"q": "foo bar"})
# -> "q=foo%20bar" (RFC 3986)

qs.encode({"q": "foo bar"}, qs.EncodeOptions(format=qs.Format.RFC1738))
# -> "q=foo+bar" (RFC 1738)
```

## Merging query parameters

If a URL already contains a query string and you want to **merge** additional parameters (without dropping existing ones), decode the current query, merge in your extras, then re‑encode exactly once. The snippet below shows a helper and a small custom transport that applies this automatically.

```python
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx
import qs_codec as qs


def merge_query(url: str, extra: dict[str, Any], options: Optional[qs.EncodeOptions] = None) -> str:
    parts = urlsplit(url)
    existing = qs.decode(parts.query) if parts.query else {}

    # Choose your policy: combine (default below), or replace last-wins via dict.update
    for k, v in extra.items():
        if k in existing:
            existing[k] = (
                [existing[k]] if not isinstance(existing[k], list) else list(existing[k])
            ) + (v if isinstance(v, list) else [v])
        else:
            existing[k] = v

    new_qs = qs.encode(existing, options) if options else qs.encode(existing)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_qs, parts.fragment))


class SmartQueryStrings(httpx.BaseTransport):
    """A transport that merges extra query params supplied via request.extensions."""

    def __init__(self, next_transport: httpx.BaseTransport) -> None:
        self.next_transport = next_transport

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        extra_params = request.extensions.get("extra_query_params", {})
        extra_params_options = request.extensions.get("extra_query_params_options", None)
        if extra_params:
            request.url = httpx.URL(
                merge_query(str(request.url), extra_params, extra_params_options)
            )
        return self.next_transport.handle_request(request)


client = httpx.Client(transport=SmartQueryStrings(httpx.HTTPTransport()))

response = client.get(
    "https://www.google.com",
    params={"a": "b", "c": "d"},
    extensions={"extra_query_params": {"c": "D", "tags": ["x", "y"]}},
)
print(response.request.url)
# -> https://www.google.com/?a=b&c=d&c=D&tags%5B0%5D=x&tags%5B1%5D=y
```

Notes:

- The helper **combines** duplicates into lists; adjust to your policy (e.g., last‑wins) as needed.
- Pass `EncodeOptions(list_format=ListFormat.REPEAT)` if your server prefers repeated keys (`tags=x&tags=y`) instead of indices (`tags[0]=x&tags[1]=y`).
- Always **decode → merge → encode** once to avoid accidental double‑encoding.

## Real‑world usage example

A common real‑world case is the **Strapi** headless CMS, which expects nested/`qs`‑style queries for filters, population, and sorting. The Python package [`strapi-client`](https://pypi.org/project/strapi-client/) uses `qs_codec` to serialize these complex query objects before making HTTPX calls. See their implementation in [`api_parameters.py`](https://github.com/Roslovets-Inc/strapi-client/blob/5bebcdad131c134fe47faca9b6e02eba0b100df1/src/strapi_client/models/api_parameters.py#L62).

With `qs_codec`, you can construct the same shape directly from nested Python data structures and pass the encoded query to HTTPX. This approach avoids brittle manual string concatenation and ensures compatibility with backends that rely on `qs` semantics.