import cgi
import contextlib
import datetime
import email.message
import json as jsonlib
import typing
import urllib.request
import warnings
from collections.abc import MutableMapping
from http.cookiejar import Cookie, CookieJar
from urllib.parse import parse_qsl, quote, unquote, urlencode

import chardet
import rfc3986
import rfc3986.exceptions

from .__version__ import __version__
from ._content_streams import ByteStream, ContentStream, encode
from ._decoders import (
    SUPPORTED_DECODERS,
    Decoder,
    IdentityDecoder,
    LineDecoder,
    MultiDecoder,
    TextDecoder,
)
from ._exceptions import (
    HTTPCORE_EXC_MAP,
    CookieConflict,
    DecodingError,
    HTTPStatusError,
    InvalidURL,
    NotRedirectResponse,
    RequestNotRead,
    ResponseClosed,
    ResponseNotRead,
    StreamConsumed,
    map_exceptions,
)
from ._status_codes import codes
from ._types import (
    CookieTypes,
    HeaderTypes,
    PrimitiveData,
    QueryParamTypes,
    RequestData,
    RequestFiles,
    URLTypes,
)
from ._utils import (
    ElapsedTimer,
    flatten_queryparams,
    guess_json_utf,
    is_known_encoding,
    normalize_header_key,
    normalize_header_value,
    obfuscate_sensitive_headers,
    parse_header_links,
    str_query_param,
)


class URL:
    def __init__(self, url: URLTypes = "", params: QueryParamTypes = None) -> None:
        if isinstance(url, str):
            try:
                self._uri_reference = rfc3986.iri_reference(url).encode()
            except rfc3986.exceptions.InvalidAuthority as exc:
                raise InvalidURL(message=str(exc)) from None

            if self.is_absolute_url:
                # We don't want to normalize relative URLs, since doing so
                # removes any leading `../` portion.
                self._uri_reference = self._uri_reference.normalize()
        else:
            self._uri_reference = url._uri_reference

        # Add any query parameters, merging with any in the URL if needed.
        if params:
            if self._uri_reference.query:
                url_params = QueryParams(self._uri_reference.query)
                url_params.update(params)
                query_string = str(url_params)
            else:
                query_string = str(QueryParams(params))
            self._uri_reference = self._uri_reference.copy_with(query=query_string)

    @property
    def scheme(self) -> str:
        return self._uri_reference.scheme or ""

    @property
    def authority(self) -> str:
        port_str = self._uri_reference.port
        default_port_str = {"https": "443", "http": "80"}.get(self.scheme, "")
        if port_str is None or port_str == default_port_str:
            return self._uri_reference.host or ""
        return self._uri_reference.authority or ""

    @property
    def userinfo(self) -> str:
        return self._uri_reference.userinfo or ""

    @property
    def username(self) -> str:
        userinfo = self._uri_reference.userinfo or ""
        return unquote(userinfo.partition(":")[0])

    @property
    def password(self) -> str:
        userinfo = self._uri_reference.userinfo or ""
        return unquote(userinfo.partition(":")[2])

    @property
    def host(self) -> str:
        return self._uri_reference.host or ""

    @property
    def port(self) -> typing.Optional[int]:
        port = self._uri_reference.port
        return int(port) if port else None

    @property
    def path(self) -> str:
        return self._uri_reference.path or "/"

    @property
    def query(self) -> str:
        return self._uri_reference.query or ""

    @property
    def full_path(self) -> str:
        path = self.path
        if self.query:
            path += "?" + self.query
        return path

    @property
    def fragment(self) -> str:
        return self._uri_reference.fragment or ""

    @property
    def raw(self) -> typing.Tuple[bytes, bytes, typing.Optional[int], bytes]:
        return (
            self.scheme.encode("ascii"),
            self.host.encode("ascii"),
            self.port,
            self.full_path.encode("ascii"),
        )

    @property
    def is_ssl(self) -> bool:
        message = 'URL.is_ssl() is pending deprecation. Use url.scheme == "https"'
        warnings.warn(message, DeprecationWarning)
        return self.scheme == "https"

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
        return bool(self.scheme and self.host)

    @property
    def is_relative_url(self) -> bool:
        return not self.is_absolute_url

    def copy_with(self, **kwargs: typing.Any) -> "URL":
        if (
            "username" in kwargs
            or "password" in kwargs
            or "host" in kwargs
            or "port" in kwargs
        ):
            host = kwargs.pop("host", self.host)
            port = kwargs.pop("port", self.port)
            username = quote(kwargs.pop("username", self.username) or "")
            password = quote(kwargs.pop("password", self.password) or "")

            authority = host
            if port is not None:
                authority += f":{port}"
            if username:
                userpass = username
                if password:
                    userpass += f":{password}"
                authority = f"{userpass}@{authority}"

            kwargs["authority"] = authority

        return URL(self._uri_reference.copy_with(**kwargs).unsplit())

    def join(self, url: URLTypes) -> "URL":
        """
        Return an absolute URL, using this URL as the base.
        """
        if self.is_relative_url:
            return URL(url)

        # We drop any fragment portion, because RFC 3986 strictly
        # treats URLs with a fragment portion as not being absolute URLs.
        base_uri = self._uri_reference.copy_with(fragment=None)
        relative_url = URL(url)
        return URL(relative_url._uri_reference.resolve_with(base_uri).unsplit())

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, (URL, str)) and str(self) == str(other)

    def __str__(self) -> str:
        return self._uri_reference.unsplit()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url_str = str(self)
        if self._uri_reference.userinfo:
            url_str = (
                rfc3986.urlparse(url_str)
                .copy_with(userinfo=f"{self.username}:[secure]")
                .unsplit()
            )
        return f"{class_name}({url_str!r})"


class QueryParams(typing.Mapping[str, str]):
    """
    URL query parameters, as a multi-dict.
    """

    def __init__(self, *args: QueryParamTypes, **kwargs: typing.Any) -> None:
        assert len(args) < 2, "Too many arguments."
        assert not (args and kwargs), "Cannot mix named and unnamed arguments."

        value = args[0] if args else kwargs

        items: typing.Sequence[typing.Tuple[str, PrimitiveData]]
        if value is None or isinstance(value, str):
            items = parse_qsl(value)
        elif isinstance(value, QueryParams):
            items = value.multi_items()
        elif isinstance(value, list):
            items = value
        else:
            items = flatten_queryparams(value)

        self._list = [(str(k), str_query_param(v)) for k, v in items]
        self._dict = {str(k): str_query_param(v) for k, v in items}

    def keys(self) -> typing.KeysView:
        return self._dict.keys()

    def values(self) -> typing.ValuesView:
        return self._dict.values()

    def items(self) -> typing.ItemsView:
        """
        Return all items in the query params. If a key occurs more than once
        only the first item for that key is returned.
        """
        return self._dict.items()

    def multi_items(self) -> typing.List[typing.Tuple[str, str]]:
        """
        Return all items in the query params. Allow duplicate keys to occur.
        """
        return list(self._list)

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        """
        Get a value from the query param for a given key. If the key occurs
        more than once, then only the first value is returned.
        """
        if key in self._dict:
            return self._dict[key]
        return default

    def get_list(self, key: typing.Any) -> typing.List[str]:
        """
        Get all values from the query param for a given key.
        """
        return [item_value for item_key, item_value in self._list if item_key == key]

    def update(self, params: QueryParamTypes = None) -> None:
        if not params:
            return

        params = QueryParams(params)
        for param in params:
            item, *extras = params.get_list(param)
            self[param] = item
            if extras:
                self._list.extend((param, e) for e in extras)
                # ensure getter matches merged QueryParams getter
                self._dict[param] = params[param]

    def __getitem__(self, key: typing.Any) -> str:
        return self._dict[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._dict[key] = value

        found_indexes = []
        for idx, (item_key, _) in enumerate(self._list):
            if item_key == key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (key, value)
        else:
            self._list.append((key, value))

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._dict

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self._list) == sorted(other._list)

    def __str__(self) -> str:
        return urlencode(self._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"

    def getlist(self, key: typing.Any) -> typing.List[str]:
        message = (
            "QueryParams.getlist() is pending deprecation. Use QueryParams.get_list()"
        )
        warnings.warn(message, DeprecationWarning)
        return self.get_list(key)


class Headers(typing.MutableMapping[str, str]):
    """
    HTTP headers, as a case-insensitive multi-dict.
    """

    def __init__(self, headers: HeaderTypes = None, encoding: str = None) -> None:
        if headers is None:
            self._list = []  # type: typing.List[typing.Tuple[bytes, bytes]]
        elif isinstance(headers, Headers):
            self._list = list(headers.raw)
        elif isinstance(headers, dict):
            self._list = [
                (normalize_header_key(k, encoding), normalize_header_value(v, encoding))
                for k, v in headers.items()
            ]
        else:
            self._list = [
                (normalize_header_key(k, encoding), normalize_header_value(v, encoding))
                for k, v in headers
            ]

        self._dict = {}  # type: typing.Dict[bytes, bytes]
        for key, value in self._list:
            if key in self._dict:
                self._dict[key] = self._dict[key] + b", " + value
            else:
                self._dict[key] = value

        self._encoding = encoding

    @property
    def encoding(self) -> str:
        """
        Header encoding is mandated as ascii, but we allow fallbacks to utf-8
        or iso-8859-1.
        """
        if self._encoding is None:
            for encoding in ["ascii", "utf-8"]:
                for key, value in self.raw:
                    try:
                        key.decode(encoding)
                        value.decode(encoding)
                    except UnicodeDecodeError:
                        break
                else:
                    # The else block runs if 'break' did not occur, meaning
                    # all values fitted the encoding.
                    self._encoding = encoding
                    break
            else:
                # The ISO-8859-1 encoding covers all 256 code points in a byte,
                # so will never raise decode errors.
                self._encoding = "iso-8859-1"
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding = value

    @property
    def raw(self) -> typing.List[typing.Tuple[bytes, bytes]]:
        """
        Returns a list of the raw header items, as byte pairs.
        """
        return list(self._list)

    def keys(self) -> typing.KeysView[str]:
        return {key.decode(self.encoding): None for key in self._dict.keys()}.keys()

    def values(self) -> typing.ValuesView[str]:
        return {
            key: value.decode(self.encoding) for key, value in self._dict.items()
        }.values()

    def items(self) -> typing.ItemsView[str, str]:
        """
        Return `(key, value)` items of headers. Concatenate headers
        into a single comma seperated value when a key occurs multiple times.
        """
        return {
            key.decode(self.encoding): value.decode(self.encoding)
            for key, value in self._dict.items()
        }.items()

    def multi_items(self) -> typing.List[typing.Tuple[str, str]]:
        """
        Return a list of `(key, value)` pairs of headers. Allow multiple
        occurences of the same key without concatenating into a single
        comma seperated value.
        """
        return [
            (key.decode(self.encoding), value.decode(self.encoding))
            for key, value in self._list
        ]

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        """
        Return a header value. If multiple occurences of the header occur
        then concatenate them together with commas.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def get_list(self, key: str, split_commas: bool = False) -> typing.List[str]:
        """
        Return a list of all header values for a given key.
        If `split_commas=True` is passed, then any comma seperated header
        values are split into multiple return strings.
        """
        get_header_key = key.lower().encode(self.encoding)

        values = [
            item_value.decode(self.encoding)
            for item_key, item_value in self._list
            if item_key == get_header_key
        ]

        if not split_commas:
            return values

        split_values = []
        for value in values:
            split_values.extend([item.strip() for item in value.split(",")])
        return split_values

    def update(self, headers: HeaderTypes = None) -> None:  # type: ignore
        headers = Headers(headers)
        for header in headers:
            self[header] = headers[header]

    def copy(self) -> "Headers":
        return Headers(dict(self.items()), encoding=self.encoding)

    def __getitem__(self, key: str) -> str:
        """
        Return a single header value.

        If there are multiple headers with the same key, then we concatenate
        them with commas. See: https://tools.ietf.org/html/rfc7230#section-3.2.2
        """
        normalized_key = key.lower().encode(self.encoding)

        items = []
        for header_key, header_value in self._list:
            if header_key == normalized_key:
                items.append(header_value.decode(self.encoding))

        if items:
            return ", ".join(items)

        raise KeyError(key)

    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """
        set_key = key.lower().encode(self._encoding or "utf-8")
        set_value = value.encode(self._encoding or "utf-8")

        self._dict[set_key] = set_value

        found_indexes = []
        for idx, (item_key, _) in enumerate(self._list):
            if item_key == set_key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (set_key, set_value)
        else:
            self._list.append((set_key, set_value))

    def __delitem__(self, key: str) -> None:
        """
        Remove the header `key`.
        """
        del_key = key.lower().encode(self.encoding)

        del self._dict[del_key]

        pop_indexes = []
        for idx, (item_key, _) in enumerate(self._list):
            if item_key == del_key:
                pop_indexes.append(idx)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def __contains__(self, key: typing.Any) -> bool:
        header_key = key.lower().encode(self.encoding)
        return header_key in self._dict

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._list)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Headers):
            return False
        return sorted(self._list) == sorted(other._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__

        encoding_str = ""
        if self.encoding != "ascii":
            encoding_str = f", encoding={self.encoding!r}"

        as_list = list(obfuscate_sensitive_headers(self.multi_items()))
        as_dict = dict(as_list)

        no_duplicate_keys = len(as_dict) == len(as_list)
        if no_duplicate_keys:
            return f"{class_name}({as_dict!r}{encoding_str})"
        return f"{class_name}({as_list!r}{encoding_str})"

    def getlist(self, key: str, split_commas: bool = False) -> typing.List[str]:
        message = "Headers.getlist() is pending deprecation. Use Headers.get_list()"
        warnings.warn(message, DeprecationWarning)
        return self.get_list(key, split_commas=split_commas)


USER_AGENT = f"python-httpx/{__version__}"
ACCEPT_ENCODING = ", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != "identity"]
)


class Request:
    def __init__(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        stream: ContentStream = None,
    ):
        self.method = method.upper()
        self.url = URL(url, params=params)
        self.headers = Headers(headers)
        if cookies:
            Cookies(cookies).set_cookie_header(self)

        if stream is not None:
            self.stream = stream
        else:
            self.stream = encode(data, files, json)

        self.timer = ElapsedTimer()
        self.prepare()

    def prepare(self) -> None:
        for key, value in self.stream.get_headers().items():
            # Ignore Transfer-Encoding if the Content-Length has been set explicitly.
            if key.lower() == "transfer-encoding" and "content-length" in self.headers:
                continue
            self.headers.setdefault(key, value)

        auto_headers: typing.List[typing.Tuple[bytes, bytes]] = []

        has_host = "host" in self.headers
        has_content_length = (
            "content-length" in self.headers or "transfer-encoding" in self.headers
        )
        has_user_agent = "user-agent" in self.headers
        has_accept = "accept" in self.headers
        has_accept_encoding = "accept-encoding" in self.headers
        has_connection = "connection" in self.headers

        if not has_host:
            url = self.url
            if url.userinfo:
                url = url.copy_with(username=None, password=None)
            auto_headers.append((b"host", url.authority.encode("ascii")))
        if not has_content_length and self.method in ("POST", "PUT", "PATCH"):
            auto_headers.append((b"content-length", b"0"))
        if not has_user_agent:
            auto_headers.append((b"user-agent", USER_AGENT.encode("ascii")))
        if not has_accept:
            auto_headers.append((b"accept", b"*/*"))
        if not has_accept_encoding:
            auto_headers.append((b"accept-encoding", ACCEPT_ENCODING.encode()))
        if not has_connection:
            auto_headers.append((b"connection", b"keep-alive"))

        self.headers = Headers(auto_headers + self.headers.raw)

    @property
    def content(self) -> bytes:
        if not hasattr(self, "_content"):
            raise RequestNotRead()
        return self._content

    def read(self) -> bytes:
        """
        Read and return the request content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join(self.stream)
            # If a streaming request has been read entirely into memory, then
            # we can replace the stream with a raw bytes implementation,
            # to ensure that any non-replayable streams can still be used.
            self.stream = ByteStream(self._content)
        return self._content

    async def aread(self) -> bytes:
        """
        Read and return the request content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join([part async for part in self.stream])
            # If a streaming request has been read entirely into memory, then
            # we can replace the stream with a raw bytes implementation,
            # to ensure that any non-replayable streams can still be used.
            self.stream = ByteStream(self._content)
        return self._content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url = str(self.url)
        return f"<{class_name}({self.method!r}, {url!r})>"


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        request: Request = None,
        http_version: str = None,
        headers: HeaderTypes = None,
        stream: ContentStream = None,
        content: bytes = None,
        history: typing.List["Response"] = None,
    ):
        self.status_code = status_code
        self.http_version = http_version
        self.headers = Headers(headers)

        self._request: typing.Optional[Request] = request

        self.call_next: typing.Optional[typing.Callable] = None

        self.history = [] if history is None else list(history)

        self.is_closed = False
        self.is_stream_consumed = False
        if stream is not None:
            self._raw_stream = stream
        else:
            self._raw_stream = ByteStream(body=content or b"")
            self.read()

    @property
    def elapsed(self) -> datetime.timedelta:
        """
        Returns the time taken for the complete request/response
        cycle to complete.
        """
        if not hasattr(self, "_elapsed"):
            raise RuntimeError(
                "'.elapsed' may only be accessed after the response "
                "has been read or closed."
            )
        return self._elapsed

    @property
    def request(self) -> Request:
        """
        Returns the request instance associated to the current response.
        """
        if self._request is None:
            raise RuntimeError(
                "The request instance has not been set on this response."
            )
        return self._request

    @request.setter
    def request(self, value: Request) -> None:
        self._request = value

    @property
    def reason_phrase(self) -> str:
        return codes.get_reason_phrase(self.status_code)

    @property
    def url(self) -> typing.Optional[URL]:
        """
        Returns the URL for which the request was made.
        """
        return self.request.url

    @property
    def content(self) -> bytes:
        if not hasattr(self, "_content"):
            raise ResponseNotRead()
        return self._content

    @property
    def text(self) -> str:
        if not hasattr(self, "_text"):
            content = self.content
            if not content:
                self._text = ""
            else:
                encoding = self.encoding
                self._text = content.decode(encoding, errors="replace")
        return self._text

    @property
    def encoding(self) -> str:
        if not hasattr(self, "_encoding"):
            encoding = self.charset_encoding
            if encoding is None or not is_known_encoding(encoding):
                encoding = self.apparent_encoding
                if encoding is None or not is_known_encoding(encoding):
                    encoding = "utf-8"
            self._encoding = encoding
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding = value

    @property
    def charset_encoding(self) -> typing.Optional[str]:
        """
        Return the encoding, as specified by the Content-Type header.
        """
        content_type = self.headers.get("Content-Type")
        if content_type is None:
            return None

        parsed = cgi.parse_header(content_type)
        media_type, params = parsed[0], parsed[-1]
        if "charset" in params:
            return params["charset"].strip("'\"")

        # RFC 2616 specifies that 'iso-8859-1' should be used as the default
        # for 'text/*' media types, if no charset is provided.
        # See: https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
        if media_type.startswith("text/"):
            return "iso-8859-1"

        return None

    @property
    def apparent_encoding(self) -> typing.Optional[str]:
        """
        Return the encoding, as it appears to autodetection.
        """
        return chardet.detect(self.content)["encoding"]

    @property
    def decoder(self) -> Decoder:
        """
        Returns a decoder instance which can be used to decode the raw byte
        content, depending on the Content-Encoding used in the response.
        """
        if not hasattr(self, "_decoder"):
            decoders: typing.List[Decoder] = []
            values = self.headers.get_list("content-encoding", split_commas=True)
            for value in values:
                value = value.strip().lower()
                try:
                    decoder_cls = SUPPORTED_DECODERS[value]
                    decoders.append(decoder_cls())
                except KeyError:
                    continue

            if len(decoders) == 1:
                self._decoder = decoders[0]
            elif len(decoders) > 1:
                self._decoder = MultiDecoder(children=decoders)
            else:
                self._decoder = IdentityDecoder()

        return self._decoder

    @property
    def is_error(self) -> bool:
        return codes.is_error(self.status_code)

    @property
    def is_redirect(self) -> bool:
        return codes.is_redirect(self.status_code) and "location" in self.headers

    def raise_for_status(self) -> None:
        """
        Raise the `HTTPStatusError` if one occurred.
        """
        message = (
            "{0.status_code} {error_type}: {0.reason_phrase} for url: {0.url}\n"
            "For more information check: https://httpstatuses.com/{0.status_code}"
        )

        request = self._request
        if request is None:
            raise RuntimeError(
                "Cannot call `raise_for_status` as the request "
                "instance has not been set on this response."
            )

        if codes.is_client_error(self.status_code):
            message = message.format(self, error_type="Client Error")
            raise HTTPStatusError(message, request=request, response=self)
        elif codes.is_server_error(self.status_code):
            message = message.format(self, error_type="Server Error")
            raise HTTPStatusError(message, request=request, response=self)

    def json(self, **kwargs: typing.Any) -> typing.Any:
        if self.charset_encoding is None and self.content and len(self.content) > 3:
            encoding = guess_json_utf(self.content)
            if encoding is not None:
                try:
                    return jsonlib.loads(self.content.decode(encoding), **kwargs)
                except UnicodeDecodeError:
                    pass
        return jsonlib.loads(self.text, **kwargs)

    @property
    def cookies(self) -> "Cookies":
        if not hasattr(self, "_cookies"):
            self._cookies = Cookies()
            self._cookies.extract_cookies(self)
        return self._cookies

    @property
    def links(self) -> typing.Dict[typing.Optional[str], typing.Dict[str, str]]:
        """
        Returns the parsed header links of the response, if any
        """
        header = self.headers.get("link")
        ldict = {}
        if header:
            links = parse_header_links(header)
            for link in links:
                key = link.get("rel") or link.get("url")
                ldict[key] = link
        return ldict

    def __repr__(self) -> str:
        return f"<Response [{self.status_code} {self.reason_phrase}]>"

    @contextlib.contextmanager
    def _wrap_decoder_errors(self) -> typing.Iterator[None]:
        # If the response has an associated request instance, we want decoding
        # errors to be raised as proper `httpx.DecodingError` exceptions.
        try:
            yield
        except ValueError as exc:
            if self._request is None:
                raise exc
            raise DecodingError(message=str(exc), request=self.request) from exc

    def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join(self.iter_bytes())
        return self._content

    def iter_bytes(self) -> typing.Iterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, and brotli encoded responses.
        """
        if hasattr(self, "_content"):
            yield self._content
        else:
            with self._wrap_decoder_errors():
                for chunk in self.iter_raw():
                    yield self.decoder.decode(chunk)
                yield self.decoder.flush()

    def iter_text(self) -> typing.Iterator[str]:
        """
        A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        decoder = TextDecoder(encoding=self.charset_encoding)
        with self._wrap_decoder_errors():
            for chunk in self.iter_bytes():
                yield decoder.decode(chunk)
            yield decoder.flush()

    def iter_lines(self) -> typing.Iterator[str]:
        decoder = LineDecoder()
        with self._wrap_decoder_errors():
            for text in self.iter_text():
                for line in decoder.decode(text):
                    yield line
            for line in decoder.flush():
                yield line

    def iter_raw(self) -> typing.Iterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if self.is_stream_consumed:
            raise StreamConsumed()
        if self.is_closed:
            raise ResponseClosed()

        self.is_stream_consumed = True
        with map_exceptions(HTTPCORE_EXC_MAP, request=self._request):
            for part in self._raw_stream:
                yield part
        self.close()

    def next(self) -> "Response":
        """
        Get the next response from a redirect response.
        """
        if not self.is_redirect:
            message = (
                "Called .next(), but the response was not a redirect. "
                "Calling code should check `response.is_redirect` first."
            )
            raise NotRedirectResponse(message)
        assert self.call_next is not None
        return self.call_next()

    def close(self) -> None:
        """
        Close the response and release the connection.
        Automatically called if the response body is read to completion.
        """
        if not self.is_closed:
            self.is_closed = True
            if self._request is not None:
                self._elapsed = self.request.timer.elapsed
            self._raw_stream.close()

    async def aread(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join([part async for part in self.aiter_bytes()])
        return self._content

    async def aiter_bytes(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, and brotli encoded responses.
        """
        if hasattr(self, "_content"):
            yield self._content
        else:
            with self._wrap_decoder_errors():
                async for chunk in self.aiter_raw():
                    yield self.decoder.decode(chunk)
                yield self.decoder.flush()

    async def aiter_text(self) -> typing.AsyncIterator[str]:
        """
        A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        decoder = TextDecoder(encoding=self.charset_encoding)
        with self._wrap_decoder_errors():
            async for chunk in self.aiter_bytes():
                yield decoder.decode(chunk)
            yield decoder.flush()

    async def aiter_lines(self) -> typing.AsyncIterator[str]:
        decoder = LineDecoder()
        with self._wrap_decoder_errors():
            async for text in self.aiter_text():
                for line in decoder.decode(text):
                    yield line
            for line in decoder.flush():
                yield line

    async def aiter_raw(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if self.is_stream_consumed:
            raise StreamConsumed()
        if self.is_closed:
            raise ResponseClosed()

        self.is_stream_consumed = True
        with map_exceptions(HTTPCORE_EXC_MAP, request=self._request):
            async for part in self._raw_stream:
                yield part
        await self.aclose()

    async def anext(self) -> "Response":
        """
        Get the next response from a redirect response.
        """
        if not self.is_redirect:
            raise NotRedirectResponse(
                "Called .anext(), but the response was not a redirect. "
                "Calling code should check `response.is_redirect` first."
            )
        assert self.call_next is not None
        return await self.call_next()

    async def aclose(self) -> None:
        """
        Close the response and release the connection.
        Automatically called if the response body is read to completion.
        """
        if not self.is_closed:
            self.is_closed = True
            if self._request is not None:
                self._elapsed = self.request.timer.elapsed
            await self._raw_stream.aclose()


class Cookies(MutableMapping):
    """
    HTTP Cookies, as a mutable mapping.
    """

    def __init__(self, cookies: CookieTypes = None) -> None:
        if cookies is None or isinstance(cookies, dict):
            self.jar = CookieJar()
            if isinstance(cookies, dict):
                for key, value in cookies.items():
                    self.set(key, value)
        elif isinstance(cookies, list):
            self.jar = CookieJar()
            for key, value in cookies:
                self.set(key, value)
        elif isinstance(cookies, Cookies):
            self.jar = CookieJar()
            for cookie in cookies.jar:
                self.jar.set_cookie(cookie)
        else:
            self.jar = cookies

    def extract_cookies(self, response: Response) -> None:
        """
        Loads any cookies based on the response `Set-Cookie` headers.
        """
        urlib_response = self._CookieCompatResponse(response)
        urllib_request = self._CookieCompatRequest(response.request)

        self.jar.extract_cookies(urlib_response, urllib_request)  # type: ignore

    def set_cookie_header(self, request: Request) -> None:
        """
        Sets an appropriate 'Cookie:' HTTP header on the `Request`.
        """
        urllib_request = self._CookieCompatRequest(request)
        self.jar.add_cookie_header(urllib_request)

    def set(self, name: str, value: str, domain: str = "", path: str = "/") -> None:
        """
        Set a cookie value by name. May optionally include domain and path.
        """
        kwargs = {
            "version": 0,
            "name": name,
            "value": value,
            "port": None,
            "port_specified": False,
            "domain": domain,
            "domain_specified": bool(domain),
            "domain_initial_dot": domain.startswith("."),
            "path": path,
            "path_specified": bool(path),
            "secure": False,
            "expires": None,
            "discard": True,
            "comment": None,
            "comment_url": None,
            "rest": {"HttpOnly": None},
            "rfc2109": False,
        }
        cookie = Cookie(**kwargs)  # type: ignore
        self.jar.set_cookie(cookie)

    def get(  # type: ignore
        self, name: str, default: str = None, domain: str = None, path: str = None
    ) -> typing.Optional[str]:
        """
        Get a cookie by name. May optionally include domain and path
        in order to specify exactly which cookie to retrieve.
        """
        value = None
        for cookie in self.jar:
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        if value is not None:
                            message = f"Multiple cookies exist with name={name}"
                            raise CookieConflict(message)
                        value = cookie.value

        if value is None:
            return default
        return value

    def delete(self, name: str, domain: str = None, path: str = None) -> None:
        """
        Delete a cookie by name. May optionally include domain and path
        in order to specify exactly which cookie to delete.
        """
        if domain is not None and path is not None:
            return self.jar.clear(domain, path, name)

        remove = []
        for cookie in self.jar:
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        remove.append(cookie)

        for cookie in remove:
            self.jar.clear(cookie.domain, cookie.path, cookie.name)

    def clear(self, domain: str = None, path: str = None) -> None:
        """
        Delete all cookies. Optionally include a domain and path in
        order to only delete a subset of all the cookies.
        """
        args = []
        if domain is not None:
            args.append(domain)
        if path is not None:
            assert domain is not None
            args.append(path)
        self.jar.clear(*args)

    def update(self, cookies: CookieTypes = None) -> None:  # type: ignore
        cookies = Cookies(cookies)
        for cookie in cookies.jar:
            self.jar.set_cookie(cookie)

    def __setitem__(self, name: str, value: str) -> None:
        return self.set(name, value)

    def __getitem__(self, name: str) -> str:
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value

    def __delitem__(self, name: str) -> None:
        return self.delete(name)

    def __len__(self) -> int:
        return len(self.jar)

    def __iter__(self) -> typing.Iterator[str]:
        return (cookie.name for cookie in self.jar)

    def __bool__(self) -> bool:
        for _ in self.jar:
            return True
        return False

    class _CookieCompatRequest(urllib.request.Request):
        """
        Wraps a `Request` instance up in a compatibility interface suitable
        for use with `CookieJar` operations.
        """

        def __init__(self, request: Request) -> None:
            super().__init__(
                url=str(request.url),
                headers=dict(request.headers),
                method=request.method,
            )
            self.request = request

        def add_unredirected_header(self, key: str, value: str) -> None:
            super().add_unredirected_header(key, value)
            self.request.headers[key] = value

    class _CookieCompatResponse:
        """
        Wraps a `Request` instance up in a compatibility interface suitable
        for use with `CookieJar` operations.
        """

        def __init__(self, response: Response):
            self.response = response

        def info(self) -> email.message.Message:
            info = email.message.Message()
            for key, value in self.response.headers.multi_items():
                #  Note that setting `info[key]` here is an "append" operation,
                # not a "replace" operation.
                # https://docs.python.org/3/library/email.compat32-message.html#email.message.Message.__setitem__
                info[key] = value
            return info
