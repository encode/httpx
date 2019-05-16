import asyncio
import cgi
import typing
from urllib.parse import parse_qsl, urlencode

import chardet
import rfc3986

from .decoders import (
    ACCEPT_ENCODING,
    SUPPORTED_DECODERS,
    Decoder,
    IdentityDecoder,
    MultiDecoder,
)
from .exceptions import (
    HttpError,
    InvalidURL,
    ResponseClosed,
    ResponseNotRead,
    StreamConsumed,
)
from .status_codes import codes
from .utils import (
    get_reason_phrase,
    is_known_encoding,
    normalize_header_key,
    normalize_header_value,
)

URLTypes = typing.Union["URL", str]

QueryParamTypes = typing.Union[
    "QueryParams",
    typing.Mapping[str, str],
    typing.List[typing.Tuple[typing.Any, typing.Any]],
    str,
]

HeaderTypes = typing.Union[
    "Headers",
    typing.Dict[typing.AnyStr, typing.AnyStr],
    typing.List[typing.Tuple[typing.AnyStr, typing.AnyStr]],
]

AuthTypes = typing.Union[
    typing.Tuple[typing.Union[str, bytes], typing.Union[str, bytes]],
    typing.Callable[["Request"], "Request"],
]

RequestData = typing.Union[dict, bytes, typing.AsyncIterator[bytes]]

ResponseContent = typing.Union[bytes, typing.AsyncIterator[bytes]]


class URL:
    def __init__(
        self,
        url: URLTypes,
        allow_relative: bool = False,
        query_params: QueryParamTypes = None,
    ) -> None:
        if isinstance(url, rfc3986.uri.URIReference):
            self.components = url
        elif isinstance(url, str):
            self.components = rfc3986.api.uri_reference(url)
        else:
            self.components = url.components

        # Handle IDNA domain names.
        if self.components.authority:
            idna_authority = self.components.authority.encode("idna").decode("ascii")
            if idna_authority != self.components.authority:
                self.components = self.components.copy_with(authority=idna_authority)

        # Normalize scheme and domain name.
        self.components = self.components.normalize()

        # Add any query parameters.
        if query_params:
            query_string = str(QueryParams(query_params))
            self.components = self.components.copy_with(query=query_string)

        # Enforce absolute URLs by default.
        if not allow_relative:
            if not self.scheme:
                raise InvalidURL("No scheme included in URL.")
            if self.scheme not in ("http", "https"):
                raise InvalidURL('URL scheme must be "http" or "https".')
            if not self.host:
                raise InvalidURL("No host included in URL.")

    @property
    def scheme(self) -> str:
        return self.components.scheme or ""

    @property
    def authority(self) -> str:
        return self.components.authority or ""

    @property
    def username(self) -> str:
        userinfo = self.components.userinfo or ""
        return userinfo.partition(":")[0]

    @property
    def password(self) -> str:
        userinfo = self.components.userinfo or ""
        return userinfo.partition(":")[2]

    @property
    def host(self) -> str:
        return self.components.host or ""

    @property
    def port(self) -> int:
        port = self.components.port
        if port is None:
            return {"https": 443, "http": 80}[self.scheme]
        return int(port)

    @property
    def path(self) -> str:
        return self.components.path or "/"

    @property
    def query(self) -> str:
        return self.components.query or ""

    @property
    def full_path(self) -> str:
        path = self.path
        if self.query:
            path += "?" + self.query
        return path

    @property
    def fragment(self) -> str:
        return self.components.fragment or ""

    @property
    def is_ssl(self) -> bool:
        return self.components.scheme == "https"

    @property
    def is_absolute_url(self) -> bool:
        """
        Return `True` for absolute URLs such as 'http://example.com/path',
        and `False` for relative URLs such as '/path'.
        """
        # We don't use rfc3986's `is_absolute` because it treats
        # URLs with a fragment portion as not absolute.
        # What we actually care about is if the URL provides
        # a scheme and hostname to which connections should be made.
        return self.components.scheme and self.components.host

    @property
    def is_relative_url(self) -> bool:
        return not self.is_absolute_url

    @property
    def origin(self) -> "Origin":
        return Origin(self)

    def copy_with(self, **kwargs: typing.Any) -> "URL":
        return URL(self.components.copy_with(**kwargs))

    def resolve_with(self, base_url: URLTypes) -> "URL":
        """
        Return an absolute URL, using base_url as the base.
        """
        # We drop any fragment portion, because RFC 3986 strictly
        # treats URLs with a fragment portion as not being absolute URLs.
        base_url = URL(base_url).copy_with(fragment=None)
        return URL(self.components.resolve_with(base_url.components))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, URL) and str(self) == str(other)

    def __str__(self) -> str:
        return self.components.unsplit()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url_str = str(self)
        return f"{class_name}({url_str!r})"


class Origin:
    """
    The URL scheme and authority information, as a comparable, hashable object.
    """

    def __init__(self, url: URLTypes) -> None:
        if not isinstance(url, URL):
            url = URL(url)
        self.is_ssl = url.is_ssl
        self.host = url.host
        self.port = url.port

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.is_ssl == other.is_ssl
            and self.host == other.host
            and self.port == other.port
        )

    def __hash__(self) -> int:
        return hash((self.is_ssl, self.host, self.port))


class QueryParams(typing.Mapping[str, str]):
    """
    URL query parameters, as a multi-dict.
    """

    def __init__(self, *args: QueryParamTypes, **kwargs: typing.Any) -> None:
        assert len(args) < 2, "Too many arguments."
        assert not (args and kwargs), "Cannot mix named and unnamed arguments."

        value = args[0] if args else kwargs

        if isinstance(value, str):
            items = parse_qsl(value)
        elif isinstance(value, QueryParams):
            items = value.multi_items()
        elif isinstance(value, list):
            items = value
        else:
            items = value.items()  # type: ignore

        self._list = [(str(k), str(v)) for k, v in items]
        self._dict = {str(k): str(v) for k, v in items}

    def getlist(self, key: typing.Any) -> typing.List[str]:
        return [item_value for item_key, item_value in self._list if item_key == key]

    def keys(self) -> typing.KeysView:
        return self._dict.keys()

    def values(self) -> typing.ValuesView:
        return self._dict.values()

    def items(self) -> typing.ItemsView:
        return self._dict.items()

    def multi_items(self) -> typing.List[typing.Tuple[str, str]]:
        return list(self._list)

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        if key in self._dict:
            return self._dict[key]
        return default

    def __getitem__(self, key: typing.Any) -> str:
        return self._dict[key]

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
        May be mutated in-place.
        """
        return self._list

    def keys(self) -> typing.List[str]:  # type: ignore
        return [key.decode(self.encoding) for key, value in self._list]

    def values(self) -> typing.List[str]:  # type: ignore
        return [value.decode(self.encoding) for key, value in self._list]

    def items(self) -> typing.List[typing.Tuple[str, str]]:  # type: ignore
        return [
            (key.decode(self.encoding), value.decode(self.encoding))
            for key, value in self._list
        ]

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        try:
            return self[key]
        except KeyError:
            return default

    def getlist(self, key: str, split_commas: bool = False) -> typing.List[str]:
        """
        Return multiple header values.
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
        set_key = key.lower().encode(self.encoding)
        set_value = value.encode(self.encoding)

        found_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
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

        pop_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == del_key:
                pop_indexes.append(idx)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def __contains__(self, key: typing.Any) -> bool:
        get_header_key = key.lower().encode(self.encoding)
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return True
        return False

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

        as_dict = dict(self.items())
        if len(as_dict) == len(self):
            return f"{class_name}({as_dict!r}{encoding_str})"
        as_list = self.items()
        return f"{class_name}({as_list!r}{encoding_str})"


class Request:
    def __init__(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
    ):
        self.method = method.upper()
        self.url = URL(url, query_params=query_params)
        self.headers = Headers(headers)

        if isinstance(data, bytes):
            self.is_streaming = False
            self.content = data
        elif isinstance(data, dict):
            self.is_streaming = False
            self.content = urlencode(data, doseq=True).encode("utf-8")
            self.headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            self.is_streaming = True
            self.content_aiter = data

    async def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "content"):
            self.content = b"".join([part async for part in self.stream()])
        return self.content

    async def stream(self) -> typing.AsyncIterator[bytes]:
        if self.is_streaming:
            async for part in self.content_aiter:
                yield part
        elif self.content:
            yield self.content

    def prepare(self) -> None:
        """
        Adds in any default headers. When using the `Client`, this will
        end up being called into by the `prepare_request()` stage.

        You can omit this behavior by calling `Client.send()` with an
        explicitly built `Request` instance.
        """
        auto_headers = []  # type: typing.List[typing.Tuple[bytes, bytes]]

        has_host = "host" in self.headers
        has_content_length = (
            "content-length" in self.headers or "transfer-encoding" in self.headers
        )
        has_accept_encoding = "accept-encoding" in self.headers

        if not has_host and self.url.authority:
            auto_headers.append((b"host", self.url.authority.encode("ascii")))
        if not has_content_length:
            if self.is_streaming:
                auto_headers.append((b"transfer-encoding", b"chunked"))
            elif self.content:
                content_length = str(len(self.content)).encode()
                auto_headers.append((b"content-length", content_length))
        if not has_accept_encoding:
            auto_headers.append((b"accept-encoding", ACCEPT_ENCODING.encode()))

        for item in reversed(auto_headers):
            self.headers.raw.insert(0, item)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url = str(self.url)
        return f"<{class_name}({self.method!r}, {url!r})>"


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        reason_phrase: str = None,
        protocol: str = None,
        headers: HeaderTypes = None,
        content: ResponseContent = b"",
        on_close: typing.Callable = None,
        request: Request = None,
        history: typing.List["Response"] = None,
    ):
        try:
            # Use a StatusCode IntEnum if possible, for a nicer representation.
            self.status_code = codes(status_code)  # type: int
        except ValueError:
            self.status_code = status_code
        self.reason_phrase = reason_phrase or get_reason_phrase(status_code)
        self.protocol = protocol
        self.headers = Headers(headers)

        if isinstance(content, bytes):
            self.is_closed = True
            self.is_stream_consumed = True
            self._raw_content = content
        else:
            self.is_closed = False
            self.is_stream_consumed = False
            self._raw_stream = content

        self.on_close = on_close
        self.request = request
        self.history = [] if history is None else list(history)
        self.next = None  # typing.Optional[typing.Callable]

    @property
    def url(self) -> typing.Optional[URL]:
        """
        Returns the URL for which the request was made.

        Requires that `request` was provided when instantiating the response.
        """
        return None if self.request is None else self.request.url

    @property
    def content(self) -> bytes:
        if not hasattr(self, "_content"):
            if hasattr(self, "_raw_content"):
                content = self.decoder.decode(self._raw_content)
                content += self.decoder.flush()
                self._content = content
            else:
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
            decoders = []  # type: typing.List[Decoder]
            values = self.headers.getlist("content-encoding", split_commas=True)
            for value in values:
                value = value.strip().lower()
                decoder_cls = SUPPORTED_DECODERS[value]
                decoders.append(decoder_cls())

            if len(decoders) == 1:
                self._decoder = decoders[0]
            elif len(decoders) > 1:
                self._decoder = MultiDecoder(decoders)
            else:
                self._decoder = IdentityDecoder()

        return self._decoder

    async def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join([part async for part in self.stream()])
        return self._content

    async def stream(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, and brotli encoded responses.
        """
        if hasattr(self, "_content"):
            yield self._content
        else:
            async for chunk in self.raw():
                yield self.decoder.decode(chunk)
            yield self.decoder.flush()

    async def raw(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if hasattr(self, "_raw_content"):
            yield self._raw_content
        else:
            if self.is_stream_consumed:
                raise StreamConsumed()
            if self.is_closed:
                raise ResponseClosed()

            self.is_stream_consumed = True
            async for part in self._raw_stream:
                yield part
            await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.
        Automatically called if the response body is read to completion.
        """
        if not self.is_closed:
            self.is_closed = True
            if self.on_close is not None:
                await self.on_close()

    @property
    def is_redirect(self) -> bool:
        return (
            self.status_code
            in (
                codes.MOVED_PERMANENTLY,
                codes.FOUND,
                codes.SEE_OTHER,
                codes.TEMPORARY_REDIRECT,
                codes.PERMANENT_REDIRECT,
            )
            and "location" in self.headers
        )

    def raise_for_status(self) -> None:
        """
        Raise the `HttpError` if one occurred.
        """
        message = (
            "{0.status_code} {error_type}: {0.reason_phrase} for url: {0.url}\n"
            "For more information check: https://httpstatuses.com/{0.status_code}"
        )

        if 400 <= self.status_code < 500:
            message = message.format(self, error_type="Client Error")
        elif 500 <= self.status_code < 600:
            message = message.format(self, error_type="Server Error")
        else:
            message = ""

        if message:
            raise HttpError(message)

    def __repr__(self) -> str:
        return f"<Response({self.status_code}, {self.reason_phrase!r})>"


class SyncResponse:
    """
    A thread-synchronous response. This class proxies onto a `Response`
    instance, providing standard synchronous interfaces where required.
    """

    def __init__(self, response: Response, loop: asyncio.AbstractEventLoop):
        self._response = response
        self._loop = loop

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def reason_phrase(self) -> str:
        return self._response.reason_phrase

    @property
    def protocol(self) -> typing.Optional[str]:
        return self._response.protocol

    @property
    def url(self) -> typing.Optional[URL]:
        return self._response.url

    @property
    def request(self) -> typing.Optional[Request]:
        return self._response.request

    @property
    def headers(self) -> Headers:
        return self._response.headers

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def encoding(self) -> str:
        return self._response.encoding

    @property
    def is_redirect(self) -> bool:
        return self._response.is_redirect

    def raise_for_status(self) -> None:
        return self._response.raise_for_status()

    def read(self) -> bytes:
        return self._loop.run_until_complete(self._response.read())

    def stream(self) -> typing.Iterator[bytes]:
        inner = self._response.stream()
        while True:
            try:
                yield self._loop.run_until_complete(inner.__anext__())
            except StopAsyncIteration:
                break

    def raw(self) -> typing.Iterator[bytes]:
        inner = self._response.raw()
        while True:
            try:
                yield self._loop.run_until_complete(inner.__anext__())
            except StopAsyncIteration:
                break

    def close(self) -> None:
        return self._loop.run_until_complete(self._response.close())

    def __repr__(self) -> str:
        return f"<Response({self.status_code}, {self.reason_phrase!r})>"
