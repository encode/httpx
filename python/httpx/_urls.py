from __future__ import annotations

import typing
from urllib.parse import unquote

import idna

from ._httpx import QueryParams
from ._types import QueryParamTypes
from ._urlparse import urlparse

__all__ = ["URL", "QueryParams"]


if not typing.TYPE_CHECKING:
    from collections.abc import Mapping

    Mapping.register(QueryParams)


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
      "http", "https", "ws", "wss", and "ftp" schemes have their port
      normalized to `None`.

      assert httpx.URL("http://example.com") == httpx.URL("http://example.com:80")
      assert httpx.URL("http://example.com").port is None
      assert httpx.URL("http://example.com:80").port is None

    * `url.userinfo` is raw bytes, without URL escaping. Usually you'll want to work
      with `url.username` and `url.password` instead, which handle the URL escaping.

    * `url.raw_path` is raw bytes of both the path and query, without URL escaping.
      This portion is used as the target when constructing HTTP requests. Usually you'll
      want to work with `url.path` instead.

    * `url.query` is raw bytes, without URL escaping. A URL query string portion can
      only be properly URL escaped when decoding the parameter names and values
      themselves.
    """

    def __init__(self, url: URL | str = "", **kwargs: typing.Any) -> None:
        if kwargs:
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

            # Perform type checking for all supported keyword arguments.
            for key, value in kwargs.items():
                if key not in allowed:
                    message = f"{key!r} is an invalid keyword argument for URL()"
                    raise TypeError(message)
                if value is not None and not isinstance(value, allowed[key]):
                    expected = allowed[key].__name__
                    seen = type(value).__name__
                    message = f"Argument {key!r} must be {expected} but got {seen}"
                    raise TypeError(message)
                if isinstance(value, bytes):
                    kwargs[key] = value.decode("ascii")

            if "params" in kwargs:
                # Replace any "params" keyword with the raw "query" instead.
                #
                # Ensure that empty params use `kwargs["query"] = None` rather
                # than `kwargs["query"] = ""`, so that generated URLs do not
                # include an empty trailing "?".
                params = kwargs.pop("params")
                kwargs["query"] = None if not params else str(QueryParams(params))

        if isinstance(url, str):
            self._uri_reference = urlparse(url, **kwargs)
        elif isinstance(url, URL):
            self._uri_reference = url._uri_reference.copy_with(**kwargs)
        else:
            raise TypeError(
                "Invalid type for url.  Expected str or httpx.URL,"
                f" got {type(url)}: {url!r}"
            )

    @property
    def scheme(self) -> str:
        """
        The URL scheme, such as "http", "https".
        Always normalised to lowercase.
        """
        return self._uri_reference.scheme

    @property
    def raw_scheme(self) -> bytes:
        """
        The raw bytes representation of the URL scheme, such as b"http", b"https".
        Always normalised to lowercase.
        """
        return self._uri_reference.scheme.encode("ascii")

    @property
    def userinfo(self) -> bytes:
        """
        The URL userinfo as a raw bytestring.
        For example: b"jo%40email.com:a%20secret".
        """
        return self._uri_reference.userinfo.encode("ascii")

    @property
    def username(self) -> str:
        """
        The URL username as a string, with URL decoding applied.
        For example: "jo@email.com"
        """
        userinfo = self._uri_reference.userinfo
        return unquote(userinfo.partition(":")[0])

    @property
    def password(self) -> str:
        """
        The URL password as a string, with URL decoding applied.
        For example: "a secret"
        """
        userinfo = self._uri_reference.userinfo
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
        host: str = self._uri_reference.host

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
        return self._uri_reference.host.encode("ascii")

    @property
    def port(self) -> int | None:
        """
        The URL port as an integer.

        Note that the URL class performs port normalization as per the WHATWG spec.
        Default ports for "http", "https", "ws", "wss", and "ftp" schemes are always
        treated as `None`.

        For example:

        assert httpx.URL("http://www.example.com") == httpx.URL("http://www.example.com:80")
        assert httpx.URL("http://www.example.com:80").port is None
        """
        return self._uri_reference.port

    @property
    def netloc(self) -> bytes:
        """
        Either `<host>` or `<host>:<port>` as bytes.
        Always normalized to lowercase, and IDNA encoded.

        This property may be used for generating the value of a request
        "Host" header.
        """
        return self._uri_reference.netloc.encode("ascii")

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
    def params(self) -> QueryParams:
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

    def copy_with(self, **kwargs: typing.Any) -> URL:
        """
        Copy this URL, returning a new URL with some components altered.
        Accepts the same set of parameters as the components that are made
        available via properties on the `URL` class.

        For example:

        url = httpx.URL("https://www.example.com").copy_with(
            username="jo@gmail.com", password="a secret"
        )
        assert url == "https://jo%40email.com:a%20secret@www.example.com"
        """
        return URL(self, **kwargs)

    def copy_set_param(self, key: str, value: typing.Any = None) -> URL:
        return self.copy_with(params=self.params.set(key, value))

    def copy_add_param(self, key: str, value: typing.Any = None) -> URL:
        return self.copy_with(params=self.params.add(key, value))

    def copy_remove_param(self, key: str) -> URL:
        return self.copy_with(params=self.params.remove(key))

    def copy_merge_params(self, params: QueryParamTypes) -> URL:
        return self.copy_with(params=self.params.merge(params))

    def join(self, url: URL | str) -> URL:
        """
        Return an absolute URL, using this URL as the base.

        Eg.

        url = httpx.URL("https://www.example.com/test")
        url = url.join("/new/path")
        assert url == "https://www.example.com/new/path"
        """
        from urllib.parse import urljoin

        return URL(urljoin(str(self), str(URL(url))))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, (URL, str)) and str(self) == str(URL(other))

    def __str__(self) -> str:
        return str(self._uri_reference)

    def __repr__(self) -> str:
        scheme, userinfo, host, port, path, query, fragment = self._uri_reference

        if ":" in userinfo:
            # Mask any password component.
            userinfo = f"{userinfo.split(':')[0]}:[secure]"

        authority = "".join(
            [
                f"{userinfo}@" if userinfo else "",
                f"[{host}]" if ":" in host else host,
                f":{port}" if port is not None else "",
            ]
        )
        url = "".join(
            [
                f"{self.scheme}:" if scheme else "",
                f"//{authority}" if authority else "",
                path,
                f"?{query}" if query is not None else "",
                f"#{fragment}" if fragment is not None else "",
            ]
        )

        return f"{self.__class__.__name__}({url!r})"

    @property
    def raw(self) -> tuple[bytes, bytes, int, bytes]:  # pragma: nocover
        import collections
        import warnings

        warnings.warn("URL.raw is deprecated.")
        RawURL = collections.namedtuple(
            "RawURL", ["raw_scheme", "raw_host", "port", "raw_path"]
        )
        return RawURL(
            raw_scheme=self.raw_scheme,
            raw_host=self.raw_host,
            port=self.port,
            raw_path=self.raw_path,
        )
