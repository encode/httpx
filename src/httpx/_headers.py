import re
import typing


__all__ = ["Headers"]


VALID_HEADER_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!#$%&'*+-.^_`|~"
)


# TODO...
#
# * Comma folded values, eg. `Vary: ...`
# * Multiple Set-Cookie headers.
# * Non-ascii support.
# * Ordering, including `Host` header exception.


def headername(name: str) -> str:
    if name.strip(VALID_HEADER_CHARS) or not name:
        raise ValueError(f"Invalid HTTP header name {name!r}.")
    return name


def headervalue(value: str) -> str:
    value = value.strip(" ")
    if not value or not value.isascii() or not value.isprintable():
        raise ValueError(f"Invalid HTTP header value {value!r}.")
    return value


class Headers(typing.Mapping[str, str]):
    def __init__(
        self,
        headers: typing.Mapping[str, str] | typing.Sequence[tuple[str, str]] | None = None,
    ) -> None:
        # {'accept': ('Accept', '*/*')}
        d: dict[str, str] = {}

        if isinstance(headers, typing.Mapping):
            # Headers({
            #    'Content-Length': '1024',
            #    'Content-Type': 'text/plain; charset=utf-8',
            # )
            d = {headername(k): headervalue(v) for k, v in headers.items()}
        elif headers is not None:
            # Headers([
            #    ('Location', 'https://www.example.com'),
            #    ('Set-Cookie', 'session_id=3498jj489jhb98jn'),
            # ])
            d = {headername(k): headervalue(v) for k, v in headers}

        self._dict = d

    def keys(self) -> typing.KeysView[str]:
        """
        Return all the header keys.

        Usage:

        h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
        assert list(h.keys()) == ["Accept", "User-Agent"]
        """
        return self._dict.keys()

    def values(self) -> typing.ValuesView[str]:
        """
        Return all the header values.

        Usage:

        h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
        assert list(h.values()) == ["*/*", "python/httpx"]
        """
        return self._dict.values()

    def items(self) -> typing.ItemsView[str, str]:
        """
        Return all headers as (key, value) tuples.

        Usage:

        h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
        assert list(h.items()) == [("Accept", "*/*"), ("User-Agent", "python/httpx")]
        """
        return self._dict.items()

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        """
        Get a value from the query param for a given key. If the key occurs
        more than once, then only the first value is returned.

        Usage:

        h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
        assert h.get("User-Agent") == "python/httpx"
        """
        for k, v in self._dict.items():
            if k.lower() == key.lower():
                return v
        return default

    def copy_set(self, key: str, value: str) -> "Headers":
        """
        Return a new Headers instance, setting the value of a key.

        Usage:

        h = httpx.Headers({"Expires": "0"})
        h = h.copy_set("Expires", "Wed, 21 Oct 2015 07:28:00 GMT")
        assert h == httpx.Headers({"Expires": "Wed, 21 Oct 2015 07:28:00 GMT"})
        """
        l = []
        seen = False

        # Either insert...
        for k, v in self._dict.items():
            if k.lower() == key.lower():
                l.append((key, value))
                seen = True
            else:
                l.append((k, v))

        # Or append...
        if not seen:
            l.append((key, value))

        return Headers(l)

    def copy_remove(self, key: str) -> "Headers":
        """
        Return a new Headers instance, removing the value of a key.

        Usage:

        h = httpx.Headers({"Accept": "*/*"})
        h = h.copy_remove("Accept")
        assert h == httpx.Headers({})
        """
        h = {k: v for k, v in self._dict.items() if k.lower() != key.lower()}
        return Headers(h)

    def copy_update(self, update: "Headers" | typing.Mapping[str, str] | None) -> "Headers":
        """
        Return a new Headers instance, removing the value of a key.

        Usage:

        h = httpx.Headers({"Accept": "*/*", "User-Agent": "python/httpx"})
        h = h.copy_update({"Accept-Encoding": "gzip"})
        assert h == httpx.Headers({"Accept": "*/*", "Accept-Encoding": "gzip", "User-Agent": "python/httpx"})
        """
        if update is None:
            return self

        new = update if isinstance(update, Headers) else Headers(update)

        # Remove updated items using a case-insensitive approach...
        keys = set([key.lower() for key in new.keys()])
        h = {k: v for k, v in self._dict.items() if k.lower() not in keys}

        # Perform the actual update...
        h.update(dict(new))

        return Headers(h)

    def __getitem__(self, key: str) -> str:
        match = key.lower()
        for k, v in self._dict.items():
            if k.lower() == match:
                return v
        raise KeyError(key)

    def __contains__(self, key: typing.Any) -> bool:
        match = key.lower()
        return any(k.lower() == match for k in self._dict.keys())

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)

    def __bool__(self) -> bool:
        return bool(self._dict)

    def __eq__(self, other: typing.Any) -> bool:
        self_lower = {k.lower(): v for k, v in self.items()}
        other_lower = {k.lower(): v for k, v in Headers(other).items()}
        return self_lower == other_lower

    def __repr__(self) -> str:
        return f"<Headers {dict(self)!r}>"


def parse_opts_header(header: str) -> tuple[str, dict[str, str]]:
    # The Content-Type header is described in RFC 2616 'Content-Type'
    # https://datatracker.ietf.org/doc/html/rfc2616#section-14.17

    # The 'type/subtype; parameter' format is described in RFC 2616 'Media Types'
    # https://datatracker.ietf.org/doc/html/rfc2616#section-3.7

    # Parameter quoting is described in RFC 2616 'Transfer Codings'
    # https://datatracker.ietf.org/doc/html/rfc2616#section-3.6

    header = header.strip()
    content_type = ''
    params = {}

    # Match the content type (up to the first semicolon or end)
    match = re.match(r'^([^;]+)', header)
    if match:
        content_type = match.group(1).strip().lower()
        rest = header[match.end():]
    else:
        return '', {}

    # Parse parameters, accounting for quoted strings
    param_pattern = re.compile(r'''
        ;\s*                             # Semicolon + optional whitespace
        (?P<key>[^=;\s]+)                # Parameter key
        =                                # Equal sign
        (?P<value>                       # Parameter value:
            "(?:[^"\\]|\\.)*"            #   Quoted string with escapes
            |                            #   OR
            [^;]*                        #   Unquoted string (until semicolon)
        )
    ''', re.VERBOSE)

    for match in param_pattern.finditer(rest):
        key = match.group('key').lower()
        value = match.group('value').strip()
        if value.startswith('"') and value.endswith('"'):
            # Remove surrounding quotes and unescape
            value = re.sub(r'\\(.)', r'\1', value[1:-1])
        params[key] = value

    return content_type, params
