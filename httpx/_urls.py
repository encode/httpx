import typing
from urllib.parse import parse_qs, quote, unquote, urlencode

import idna
import rfc3986
import rfc3986.exceptions

from ._exceptions import InvalidURL
from ._types import PrimitiveData, QueryParamTypes, URLTypes
from ._utils import primitive_value_to_str


class URL:
    """
    url = httpx.URL("HTTPS://jo%40email.com:a%20secret@müller.de:1234/pa%20th?search=ab#anchorlink")

    assert url.scheme == "https"
    assert url.username == "jo@email.com"
    assert url.password == "a secret"
    assert url.userinfo == b"jo%40email.com:a%20secret"
    assert url.host == "müller.de"
    assert url.raw_host == b"xn--mller-kva.de"
    assert url.port == 1234
    assert url.netloc == b"xn--mller-kva.de:1234"
    assert url.path == "/pa th"
    assert url.query == b"?search=ab"
    assert url.raw_path == b"/pa%20th?search=ab"
    assert url.fragment == "anchorlink"

    The components of a URL are broken down like this:

       https://jo%40email.com:a%20secret@müller.de:1234/pa%20th?search=ab#anchorlink
    [scheme]   [  username  ] [password] [ host ][port][ path ] [ query ] [fragment]
               [       userinfo        ] [   netloc   ][    raw_path    ]

    Note that:

    * `url.scheme` is normalized to always be lowercased.

    * `url.host` is normalized to always be lowercased. Internationalized domain
      names are represented in unicode, without IDNA encoding applied. For instance:

      url = httpx.URL("http://中国.icom.museum")
      assert url.host == "中国.icom.museum"
      url = httpx.URL("http://xn--fiqs8s.icom.museum")
      assert url.host == "中国.icom.museum"

    * `url.raw_host` is normalized to always be lowercased, and is IDNA encoded.

      url = httpx.URL("http://中国.icom.museum")
      assert url.raw_host == b"xn--fiqs8s.icom.museum"
      url = httpx.URL("http://xn--fiqs8s.icom.museum")
      assert url.raw_host == b"xn--fiqs8s.icom.museum"

    * `url.port` is either None or an integer. URLs that include the default port for
      "http", "https", "ws", "wss", and "ftp" schemes have their port normalized to `None`.

      assert httpx.URL("http://example.com") == httpx.URL("http://example.com:80")
      assert httpx.URL("http://example.com").port is None
      assert httpx.URL("http://example.com:80").port is None

    * `url.userinfo` is raw bytes, without URL escaping. Usually you'll want to work with
      `url.username` and `url.password` instead, which handle the URL escaping.

    * `url.raw_path` is raw bytes of both the path and query, without URL escaping.
      This portion is used as the target when constructing HTTP requests. Usually you'll
      want to work with `url.path` instead.

    * `url.query` is raw bytes, without URL escaping. A URL query string portion can only
      be properly URL escaped when decoding the parameter names and values themselves.
    """

    def __init__(
        self, url: typing.Union["URL", str] = "", **kwargs: typing.Any
    ) -> None:
        if isinstance(url, str):
            try:
                self._uri_reference = rfc3986.iri_reference(url).encode()
            except rfc3986.exceptions.InvalidAuthority as exc:
                raise InvalidURL(message=str(exc)) from None

            if self.is_absolute_url:
                # We don't want to normalize relative URLs, since doing so
                # removes any leading `../` portion.
                self._uri_reference = self._uri_reference.normalize()
        elif isinstance(url, URL):
            self._uri_reference = url._uri_reference
        else:
            raise TypeError(
                f"Invalid type for url.  Expected str or httpx.URL, got {type(url)}: {url!r}"
            )

        # Perform port normalization, following the WHATWG spec for default ports.
        #
        # See:
        # * https://tools.ietf.org/html/rfc3986#section-3.2.3
        # * https://url.spec.whatwg.org/#url-miscellaneous
        # * https://url.spec.whatwg.org/#scheme-state
        default_port = {
            "ftp": ":21",
            "http": ":80",
            "https": ":443",
            "ws": ":80",
            "wss": ":443",
        }.get(self._uri_reference.scheme, "")
        authority = self._uri_reference.authority or ""
        if default_port and authority.endswith(default_port):
            authority = authority[: -len(default_port)]
            self._uri_reference = self._uri_reference.copy_with(authority=authority)

        if kwargs:
            self._uri_reference = self.copy_with(**kwargs)._uri_reference

    @property
    def scheme(self) -> str:
        """
        The URL scheme, such as "http", "https".
        Always normalised to lowercase.
        """
        return self._uri_reference.scheme or ""

    @property
    def raw_scheme(self) -> bytes:
        """
        The raw bytes representation of the URL scheme, such as b"http", b"https".
        Always normalised to lowercase.
        """
        return self.scheme.encode("ascii")

    @property
    def userinfo(self) -> bytes:
        """
        The URL userinfo as a raw bytestring.
        For example: b"jo%40email.com:a%20secret".
        """
        userinfo = self._uri_reference.userinfo or ""
        return userinfo.encode("ascii")

    @property
    def username(self) -> str:
        """
        The URL username as a string, with URL decoding applied.
        For example: "jo@email.com"
        """
        userinfo = self._uri_reference.userinfo or ""
        return unquote(userinfo.partition(":")[0])

    @property
    def password(self) -> str:
        """
        The URL password as a string, with URL decoding applied.
        For example: "a secret"
        """
        userinfo = self._uri_reference.userinfo or ""
        return unquote(userinfo.partition(":")[2])

    @property
    def host(self) -> str:
        """
        The URL host as a string.
        Always normalized to lowercase, with IDNA hosts decoded into unicode.

        Examples:

        url = httpx.URL("http://www.EXAMPLE.org")
        assert url.host == "www.example.org"

        url = httpx.URL("http://中国.icom.museum")
        assert url.host == "中国.icom.museum"

        url = httpx.URL("http://xn--fiqs8s.icom.museum")
        assert url.host == "中国.icom.museum"

        url = httpx.URL("https://[::ffff:192.168.0.1]")
        assert url.host == "::ffff:192.168.0.1"
        """
        host: str = self._uri_reference.host or ""

        if host and ":" in host and host[0] == "[":
            # it's an IPv6 address
            host = host.lstrip("[").rstrip("]")

        if host.startswith("xn--"):
            host = idna.decode(host)

        return host

    @property
    def raw_host(self) -> bytes:
        """
        The raw bytes representation of the URL host.
        Always normalized to lowercase, and IDNA encoded.

        Examples:

        url = httpx.URL("http://www.EXAMPLE.org")
        assert url.raw_host == b"www.example.org"

        url = httpx.URL("http://中国.icom.museum")
        assert url.raw_host == b"xn--fiqs8s.icom.museum"

        url = httpx.URL("http://xn--fiqs8s.icom.museum")
        assert url.raw_host == b"xn--fiqs8s.icom.museum"

        url = httpx.URL("https://[::ffff:192.168.0.1]")
        assert url.raw_host == b"::ffff:192.168.0.1"
        """
        host: str = self._uri_reference.host or ""

        if host and ":" in host and host[0] == "[":
            # it's an IPv6 address
            host = host.lstrip("[").rstrip("]")

        return host.encode("ascii")

    @property
    def port(self) -> typing.Optional[int]:
        """
        The URL port as an integer.

        Note that the URL class performs port normalization as per the WHATWG spec.
        Default ports for "http", "https", "ws", "wss", and "ftp" schemes are always
        treated as `None`.

        For example:

        assert httpx.URL("http://www.example.com") == httpx.URL("http://www.example.com:80")
        assert httpx.URL("http://www.example.com:80").port is None
        """
        port = self._uri_reference.port
        return int(port) if port else None

    @property
    def netloc(self) -> bytes:
        """
        Either `<host>` or `<host>:<port>` as bytes.
        Always normalized to lowercase, and IDNA encoded.

        This property may be used for generating the value of a request
        "Host" header.
        """
        host = self._uri_reference.host or ""
        port = self._uri_reference.port
        netloc = host.encode("ascii")
        if port:
            netloc = netloc + b":" + port.encode("ascii")
        return netloc

    @property
    def path(self) -> str:
        """
        The URL path as a string. Excluding the query string, and URL decoded.

        For example:

        url = httpx.URL("https://example.com/pa%20th")
        assert url.path == "/pa th"
        """
        path = self._uri_reference.path or "/"
        return unquote(path)

    @property
    def query(self) -> bytes:
        """
        The URL query string, as raw bytes, excluding the leading b"?".

        This is necessarily a bytewise interface, because we cannot
        perform URL decoding of this representation until we've parsed
        the keys and values into a QueryParams instance.

        For example:

        url = httpx.URL("https://example.com/?filter=some%20search%20terms")
        assert url.query == b"filter=some%20search%20terms"
        """
        query = self._uri_reference.query or ""
        return query.encode("ascii")

    @property
    def params(self) -> "QueryParams":
        """
        The URL query parameters, neatly parsed and packaged into an immutable
        multidict representation.
        """
        return QueryParams(self._uri_reference.query)

    @property
    def raw_path(self) -> bytes:
        """
        The complete URL path and query string as raw bytes.
        Used as the target when constructing HTTP requests.

        For example:

        GET /users?search=some%20text HTTP/1.1
        Host: www.example.org
        Connection: close
        """
        path = self._uri_reference.path or "/"
        if self._uri_reference.query is not None:
            path += "?" + self._uri_reference.query
        return path.encode("ascii")

    @property
    def fragment(self) -> str:
        """
        The URL fragments, as used in HTML anchors.
        As a string, without the leading '#'.
        """
        return unquote(self._uri_reference.fragment or "")

    @property
    def is_absolute_url(self) -> bool:
        """
        Return `True` for absolute URLs such as 'http://example.com/path',
        and `False` for relative URLs such as '/path'.
        """
        # We don't use `.is_absolute` from `rfc3986` because it treats
        # URLs with a fragment portion as not absolute.
        # What we actually care about is if the URL provides
        # a scheme and hostname to which connections should be made.
        return bool(self._uri_reference.scheme and self._uri_reference.host)

    @property
    def is_relative_url(self) -> bool:
        """
        Return `False` for absolute URLs such as 'http://example.com/path',
        and `True` for relative URLs such as '/path'.
        """
        return not self.is_absolute_url

    def copy_with(self, **kwargs: typing.Any) -> "URL":
        """
        Copy this URL, returning a new URL with some components altered.
        Accepts the same set of parameters as the components that are made
        available via properties on the `URL` class.

        For example:

        url = httpx.URL("https://www.example.com").copy_with(username="jo@gmail.com", password="a secret")
        assert url == "https://jo%40email.com:a%20secret@www.example.com"
        """
        allowed = {
            "scheme": str,
            "username": str,
            "password": str,
            "userinfo": bytes,
            "host": str,
            "port": int,
            "netloc": bytes,
            "path": str,
            "query": bytes,
            "raw_path": bytes,
            "fragment": str,
            "params": object,
        }

        # Step 1
        # ======
        #
        # Perform type checking for all supported keyword arguments.
        for key, value in kwargs.items():
            if key not in allowed:
                message = f"{key!r} is an invalid keyword argument for copy_with()"
                raise TypeError(message)
            if value is not None and not isinstance(value, allowed[key]):
                expected = allowed[key].__name__
                seen = type(value).__name__
                message = f"Argument {key!r} must be {expected} but got {seen}"
                raise TypeError(message)

        # Step 2
        # ======
        #
        # Consolidate "username", "password", "userinfo", "host", "port" and "netloc"
        # into a single "authority" keyword, for `rfc3986`.
        if "username" in kwargs or "password" in kwargs:
            # Consolidate "username" and "password" into "userinfo".
            username = quote(kwargs.pop("username", self.username) or "")
            password = quote(kwargs.pop("password", self.password) or "")
            userinfo = f"{username}:{password}" if password else username
            kwargs["userinfo"] = userinfo.encode("ascii")

        if "host" in kwargs or "port" in kwargs:
            # Consolidate "host" and "port" into "netloc".
            host = kwargs.pop("host", self.host) or ""
            port = kwargs.pop("port", self.port)

            if host and ":" in host and host[0] != "[":
                # IPv6 addresses need to be escaped within square brackets.
                host = f"[{host}]"

            kwargs["netloc"] = (
                f"{host}:{port}".encode("ascii")
                if port is not None
                else host.encode("ascii")
            )

        if "userinfo" in kwargs or "netloc" in kwargs:
            # Consolidate "userinfo" and "netloc" into authority.
            userinfo = (kwargs.pop("userinfo", self.userinfo) or b"").decode("ascii")
            netloc = (kwargs.pop("netloc", self.netloc) or b"").decode("ascii")
            authority = f"{userinfo}@{netloc}" if userinfo else netloc
            kwargs["authority"] = authority

        # Step 3
        # ======
        #
        # Wrangle any "path", "query", "raw_path" and "params" keywords into
        # "query" and "path" keywords for `rfc3986`.
        if "raw_path" in kwargs:
            # If "raw_path" is included, then split it into "path" and "query" components.
            raw_path = kwargs.pop("raw_path") or b""
            path, has_query, query = raw_path.decode("ascii").partition("?")
            kwargs["path"] = path
            kwargs["query"] = query if has_query else None

        else:
            if kwargs.get("path") is not None:
                # Ensure `kwargs["path"] = <url quoted str>` for `rfc3986`.
                kwargs["path"] = quote(kwargs["path"])

            if kwargs.get("query") is not None:
                # Ensure `kwargs["query"] = <str>` for `rfc3986`.
                #
                # Note that `.copy_with(query=None)` and `.copy_with(query=b"")`
                # are subtly different. The `None` style will not include an empty
                # trailing "?" character.
                kwargs["query"] = kwargs["query"].decode("ascii")

            if "params" in kwargs:
                # Replace any "params" keyword with the raw "query" instead.
                #
                # Ensure that empty params use `kwargs["query"] = None` rather
                # than `kwargs["query"] = ""`, so that generated URLs do not
                # include an empty trailing "?".
                params = kwargs.pop("params")
                kwargs["query"] = None if not params else str(QueryParams(params))

        # Step 4
        # ======
        #
        # Ensure any fragment component is quoted.
        if kwargs.get("fragment") is not None:
            kwargs["fragment"] = quote(kwargs["fragment"])

        # Step 5
        # ======
        #
        # At this point kwargs may include keys for "scheme", "authority", "path",
        # "query" and "fragment". Together these constitute the entire URL.
        #
        # See https://tools.ietf.org/html/rfc3986#section-3
        #
        #  foo://example.com:8042/over/there?name=ferret#nose
        #  \_/   \______________/\_________/ \_________/ \__/
        #   |           |            |            |        |
        # scheme     authority       path        query   fragment
        new_url = URL(self)
        new_url._uri_reference = self._uri_reference.copy_with(**kwargs)
        if new_url.is_absolute_url:
            new_url._uri_reference = new_url._uri_reference.normalize()
        return URL(new_url)

    def copy_set_param(self, key: str, value: typing.Any = None) -> "URL":
        return self.copy_with(params=self.params.set(key, value))

    def copy_add_param(self, key: str, value: typing.Any = None) -> "URL":
        return self.copy_with(params=self.params.add(key, value))

    def copy_remove_param(self, key: str) -> "URL":
        return self.copy_with(params=self.params.remove(key))

    def copy_merge_params(self, params: QueryParamTypes) -> "URL":
        return self.copy_with(params=self.params.merge(params))

    def join(self, url: URLTypes) -> "URL":
        """
        Return an absolute URL, using this URL as the base.

        Eg.

        url = httpx.URL("https://www.example.com/test")
        url = url.join("/new/path")
        assert url == "https://www.example.com/new/path"
        """
        if self.is_relative_url:
            # Workaround to handle relative URLs, which otherwise raise
            # rfc3986.exceptions.ResolutionError when used as an argument
            # in `.resolve_with`.
            return (
                self.copy_with(scheme="http", host="example.com")
                .join(url)
                .copy_with(scheme=None, host=None)
            )

        # We drop any fragment portion, because RFC 3986 strictly
        # treats URLs with a fragment portion as not being absolute URLs.
        base_uri = self._uri_reference.copy_with(fragment=None)
        relative_url = URL(url)
        return URL(relative_url._uri_reference.resolve_with(base_uri).unsplit())

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, (URL, str)) and str(self) == str(URL(other))

    def __str__(self) -> str:
        return self._uri_reference.unsplit()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url_str = str(self)
        if self._uri_reference.userinfo:
            # Mask any password component in the URL representation, to lower the
            # risk of unintended leakage, such as in debug information and logging.
            username = quote(self.username)
            url_str = (
                rfc3986.urlparse(url_str)
                .copy_with(userinfo=f"{username}:[secure]")
                .unsplit()
            )
        return f"{class_name}({url_str!r})"


class QueryParams(typing.Mapping[str, str]):
    """
    URL query parameters, as a multi-dict.
    """

    def __init__(
        self, *args: typing.Optional[QueryParamTypes], **kwargs: typing.Any
    ) -> None:
        assert len(args) < 2, "Too many arguments."
        assert not (args and kwargs), "Cannot mix named and unnamed arguments."

        value = args[0] if args else kwargs

        items: typing.Sequence[typing.Tuple[str, PrimitiveData]]
        if value is None or isinstance(value, (str, bytes)):
            value = value.decode("ascii") if isinstance(value, bytes) else value
            self._dict = parse_qs(value, keep_blank_values=True)
        elif isinstance(value, QueryParams):
            self._dict = {k: list(v) for k, v in value._dict.items()}
        else:
            dict_value: typing.Dict[typing.Any, typing.List[typing.Any]] = {}
            if isinstance(value, (list, tuple)):
                # Convert list inputs like:
                #     [("a", "123"), ("a", "456"), ("b", "789")]
                # To a dict representation, like:
                #     {"a": ["123", "456"], "b": ["789"]}
                for item in value:
                    dict_value.setdefault(item[0], []).append(item[1])
            else:
                # Convert dict inputs like:
                #    {"a": "123", "b": ["456", "789"]}
                # To dict inputs where values are always lists, like:
                #    {"a": ["123"], "b": ["456", "789"]}
                dict_value = {
                    k: list(v) if isinstance(v, (list, tuple)) else [v]
                    for k, v in value.items()
                }

            # Ensure that keys and values are neatly coerced to strings.
            # We coerce values `True` and `False` to JSON-like "true" and "false"
            # representations, and coerce `None` values to the empty string.
            self._dict = {
                str(k): [primitive_value_to_str(item) for item in v]
                for k, v in dict_value.items()
            }

    def keys(self) -> typing.KeysView:
        """
        Return all the keys in the query params.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.keys()) == ["a", "b"]
        """
        return self._dict.keys()

    def values(self) -> typing.ValuesView:
        """
        Return all the values in the query params. If a key occurs more than once
        only the first item for that key is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.values()) == ["123", "789"]
        """
        return {k: v[0] for k, v in self._dict.items()}.values()

    def items(self) -> typing.ItemsView:
        """
        Return all items in the query params. If a key occurs more than once
        only the first item for that key is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.items()) == [("a", "123"), ("b", "789")]
        """
        return {k: v[0] for k, v in self._dict.items()}.items()

    def multi_items(self) -> typing.List[typing.Tuple[str, str]]:
        """
        Return all items in the query params. Allow duplicate keys to occur.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.multi_items()) == [("a", "123"), ("a", "456"), ("b", "789")]
        """
        multi_items: typing.List[typing.Tuple[str, str]] = []
        for k, v in self._dict.items():
            multi_items.extend([(k, i) for i in v])
        return multi_items

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        """
        Get a value from the query param for a given key. If the key occurs
        more than once, then only the first value is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert q.get("a") == "123"
        """
        if key in self._dict:
            return self._dict[str(key)][0]
        return default

    def get_list(self, key: str) -> typing.List[str]:
        """
        Get all values from the query param for a given key.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert q.get_list("a") == ["123", "456"]
        """
        return list(self._dict.get(str(key), []))

    def set(self, key: str, value: typing.Any = None) -> "QueryParams":
        """
        Return a new QueryParams instance, setting the value of a key.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.set("a", "456")
        assert q == httpx.QueryParams("a=456")
        """
        q = QueryParams()
        q._dict = dict(self._dict)
        q._dict[str(key)] = [primitive_value_to_str(value)]
        return q

    def add(self, key: str, value: typing.Any = None) -> "QueryParams":
        """
        Return a new QueryParams instance, setting or appending the value of a key.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.add("a", "456")
        assert q == httpx.QueryParams("a=123&a=456")
        """
        q = QueryParams()
        q._dict = dict(self._dict)
        q._dict[str(key)] = q.get_list(key) + [primitive_value_to_str(value)]
        return q

    def remove(self, key: str) -> "QueryParams":
        """
        Return a new QueryParams instance, removing the value of a key.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.remove("a")
        assert q == httpx.QueryParams("")
        """
        q = QueryParams()
        q._dict = dict(self._dict)
        q._dict.pop(str(key), None)
        return q

    def merge(self, params: typing.Optional[QueryParamTypes] = None) -> "QueryParams":
        """
        Return a new QueryParams instance, updated with.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.merge({"b": "456"})
        assert q == httpx.QueryParams("a=123&b=456")

        q = httpx.QueryParams("a=123")
        q = q.merge({"a": "456", "b": "789"})
        assert q == httpx.QueryParams("a=456&b=789")
        """
        q = QueryParams(params)
        q._dict = {**self._dict, **q._dict}
        return q

    def __getitem__(self, key: typing.Any) -> str:
        return self._dict[key][0]

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._dict

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)

    def __bool__(self) -> bool:
        return bool(self._dict)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self.multi_items()) == sorted(other.multi_items())

    def __str__(self) -> str:
        return urlencode(self.multi_items())

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"

    def update(self, params: typing.Optional[QueryParamTypes] = None) -> None:
        raise RuntimeError(
            "QueryParams are immutable since 0.18.0. "
            "Use `q = q.merge(...)` to create an updated copy."
        )

    def __setitem__(self, key: str, value: str) -> None:
        raise RuntimeError(
            "QueryParams are immutable since 0.18.0. "
            "Use `q = q.set(key, value)` to create an updated copy."
        )
