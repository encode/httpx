import http
import typing
from urllib.parse import urlsplit

from .config import SSLConfig, TimeoutConfig
from .decoders import (
    ACCEPT_ENCODING,
    SUPPORTED_DECODERS,
    Decoder,
    IdentityDecoder,
    MultiDecoder,
)
from .exceptions import ResponseClosed, StreamConsumed
from .utils import normalize_header_key, normalize_header_value


class URL:
    def __init__(self, url: str = "") -> None:
        self.components = urlsplit(url)
        if not self.components.scheme:
            raise ValueError("No scheme included in URL.")
        if self.components.scheme not in ("http", "https"):
            raise ValueError('URL scheme must be "http" or "https".')
        if not self.components.hostname:
            raise ValueError("No hostname included in URL.")

    @property
    def scheme(self) -> str:
        return self.components.scheme

    @property
    def netloc(self) -> str:
        return self.components.netloc

    @property
    def path(self) -> str:
        return self.components.path

    @property
    def query(self) -> str:
        return self.components.query

    @property
    def fragment(self) -> str:
        return self.components.fragment

    @property
    def hostname(self) -> str:
        return self.components.hostname

    @property
    def port(self) -> int:
        port = self.components.port
        if port is None:
            return {"https": 443, "http": 80}[self.scheme]
        return port

    @property
    def full_path(self) -> str:
        path = self.path or "/"
        query = self.query
        if query:
            return path + "?" + query
        return path

    @property
    def is_secure(self) -> bool:
        return self.components.scheme == "https"

    @property
    def origin(self) -> "Origin":
        return Origin(self)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, URL) and str(self) == str(other)

    def __str__(self) -> str:
        return self.components.geturl()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url_str = str(self)
        return f"{class_name}({url_str!r})"


class Origin:
    def __init__(self, url: typing.Union[str, URL]) -> None:
        if isinstance(url, str):
            url = URL(url)
        self.is_ssl = url.scheme == "https"
        self.hostname = url.hostname.lower()
        self.port = url.port

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.is_ssl == other.is_ssl
            and self.hostname == other.hostname
            and self.port == other.port
        )

    def __hash__(self) -> int:
        return hash((self.is_ssl, self.hostname, self.port))


HeaderTypes = typing.Union[
    "Headers",
    typing.Dict[typing.AnyStr, typing.AnyStr],
    typing.List[typing.Tuple[typing.AnyStr, typing.AnyStr]],
]


class Headers(typing.MutableMapping[str, str]):
    """
    A case-insensitive multidict.
    """

    def __init__(self, headers: HeaderTypes = None) -> None:
        if headers is None:
            self._list = []  # type: typing.List[typing.Tuple[bytes, bytes]]
        elif isinstance(headers, Headers):
            self._list = list(headers.raw)
        elif isinstance(headers, dict):
            self._list = [
                (normalize_header_key(k), normalize_header_value(v))
                for k, v in headers.items()
            ]
        else:
            self._list = [
                (normalize_header_key(k), normalize_header_value(v)) for k, v in headers
            ]

    @property
    def raw(self) -> typing.List[typing.Tuple[bytes, bytes]]:
        return self._list

    def keys(self) -> typing.List[str]:  # type: ignore
        return [key.decode("latin-1") for key, value in self._list]

    def values(self) -> typing.List[str]:  # type: ignore
        return [value.decode("latin-1") for key, value in self._list]

    def items(self) -> typing.List[typing.Tuple[str, str]]:  # type: ignore
        return [
            (key.decode("latin-1"), value.decode("latin-1"))
            for key, value in self._list
        ]

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        try:
            return self[key]
        except KeyError:
            return default

    def getlist(self, key: str) -> typing.List[str]:
        get_header_key = key.lower().encode("latin-1")
        return [
            item_value.decode("latin-1")
            for item_key, item_value in self._list
            if item_key == get_header_key
        ]

    def __getitem__(self, key: str) -> str:
        get_header_key = key.lower().encode("latin-1")
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return header_value.decode("latin-1")
        raise KeyError(key)

    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """
        set_key = key.lower().encode("latin-1")
        set_value = value.encode("latin-1")

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
        del_key = key.lower().encode("latin-1")

        pop_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == del_key:
                pop_indexes.append(idx)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def __contains__(self, key: typing.Any) -> bool:
        get_header_key = key.lower().encode("latin-1")
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
        as_dict = dict(self.items())
        if len(as_dict) == len(self):
            return f"{class_name}({as_dict!r})"
        return f"{class_name}(raw={self.raw!r})"


class Request:
    def __init__(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        headers: HeaderTypes = None,
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
    ):
        self.method = method.upper()
        self.url = URL(url) if isinstance(url, str) else url
        if isinstance(body, bytes):
            self.is_streaming = False
            self.body = body
        else:
            self.is_streaming = True
            self.body_aiter = body
        self.headers = Headers(headers)

    async def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "body"):
            body = b""
            async for part in self.stream():
                body += part
            self.body = body
        return self.body

    async def stream(self) -> typing.AsyncIterator[bytes]:
        if self.is_streaming:
            async for part in self.body_aiter:
                yield part
        elif self.body:
            yield self.body

    def prepare(self) -> None:
        auto_headers = []  # type: typing.List[typing.Tuple[bytes, bytes]]

        has_host = "host" in self.headers
        has_content_length = (
            "content-length" in self.headers or "transfer-encoding" in self.headers
        )
        has_accept_encoding = "accept-encoding" in self.headers

        if not has_host:
            auto_headers.append((b"host", self.url.netloc.encode("ascii")))
        if not has_content_length:
            if self.is_streaming:
                auto_headers.append((b"transfer-encoding", b"chunked"))
            elif self.body:
                content_length = str(len(self.body)).encode()
                auto_headers.append((b"content-length", content_length))
        if not has_accept_encoding:
            auto_headers.append((b"accept-encoding", ACCEPT_ENCODING.encode()))

        for item in reversed(auto_headers):
            self.headers.raw.insert(0, item)


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        reason: typing.Optional[str] = None,
        protocol: typing.Optional[str] = None,
        headers: typing.List[typing.Tuple[bytes, bytes]] = [],
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        on_close: typing.Callable = None,
        request: Request = None,
        history: typing.List["Response"] = None,
    ):
        self.status_code = status_code
        if not reason:
            try:
                self.reason = http.HTTPStatus(status_code).phrase
            except ValueError as exc:
                self.reason = ""
        else:
            self.reason = reason
        self.protocol = protocol
        self.headers = Headers(headers)
        self.on_close = on_close
        self.is_closed = False
        self.is_streamed = False

        decoders = []  # type: typing.List[Decoder]
        value = self.headers.get("content-encoding", "identity")
        for part in value.split(","):
            part = part.strip().lower()
            decoder_cls = SUPPORTED_DECODERS[part]
            decoders.append(decoder_cls())

        if len(decoders) == 0:
            self.decoder = IdentityDecoder()  # type: Decoder
        elif len(decoders) == 1:
            self.decoder = decoders[0]
        else:
            self.decoder = MultiDecoder(decoders)

        if isinstance(body, bytes):
            self.is_closed = True
            self.body = self.decoder.decode(body) + self.decoder.flush()
        else:
            self.body_aiter = body

        self.request = request
        self.history = [] if history is None else list(history)
        self.next = None  # typing.Optional[typing.Callable]

    @property
    def url(self) -> typing.Optional[URL]:
        return None if self.request is None else self.request.url

    async def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "body"):
            body = b""
            async for part in self.stream():
                body += part
            self.body = body
        return self.body

    async def stream(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, and brotli encoded responses.
        """
        if hasattr(self, "body"):
            yield self.body
        else:
            async for chunk in self.raw():
                yield self.decoder.decode(chunk)
            yield self.decoder.flush()

    async def raw(self) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if self.is_streamed:
            raise StreamConsumed()
        if self.is_closed:
            raise ResponseClosed()
        self.is_streamed = True
        async for part in self.body_aiter:
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
            self.status_code in (301, 302, 303, 307, 308) and "location" in self.headers
        )
