import typing

PrimitiveData = typing.Optional[typing.Union[str, int, float, bool]]
QueryParamTypes = typing.Union[
    "QueryParams",
    typing.Mapping[str, typing.Union[PrimitiveData, typing.Sequence[PrimitiveData]]],
    typing.List[typing.Tuple[str, PrimitiveData]],
    typing.Tuple[typing.Tuple[str, PrimitiveData], ...],
    str,
    bytes,
]


@typing.final
class QueryParams(typing.Mapping[str, str]):
    def __new__(cls, *args: QueryParamTypes | None, **kwargs: typing.Any) -> None:...
    def keys(self) -> typing.KeysView[str]:
        """
        Return all the keys in the query params.

        Usage:

        ```
        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.keys()) == ["a", "b"]
        ```
        """

    def values(self) -> typing.ValuesView[str]:
        """
        Return all the values in the query params. If a key occurs more than once
        only the first item for that key is returned.

        Usage:

        ```
        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.values()) == ["123", "789"]
        ```
        """

    def items(self) -> typing.ItemsView[str, str]:
        """
        Return all items in the query params. If a key occurs more than once
        only the first item for that key is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.items()) == [("a", "123"), ("b", "789")]
        """

    def multi_items(self) -> list[tuple[str, str]]:
        """
        Return all items in the query params. Allow duplicate keys to occur.

        Usage:

        ```
        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.multi_items()) == [("a", "123"), ("a", "456"), ("b", "789")]
        ```
        """

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        """
        Get a value from the query param for a given key. If the key occurs
        more than once, then only the first value is returned.

        Usage:

        ```
        q = httpx.QueryParams("a=123&a=456&b=789")
        assert q.get("a") == "123"
        ```
        """

    def get_list(self, key: str) -> list[str]:
        """
        Get all values from the query param for a given key.

        Usage:

        ```
        q = httpx.QueryParams("a=123&a=456&b=789")
        assert q.get_list("a") == ["123", "456"]
        ```
        """

    def set(self, key: str, value: typing.Any = None) -> QueryParams:
        """
        Return a new QueryParams instance, setting the value of a key.

        Usage:

        ```
        q = httpx.QueryParams("a=123")
        q = q.set("a", "456")
        assert q == httpx.QueryParams("a=456")
        ```
        """

    def add(self, key: str, value: typing.Any = None) -> QueryParams:
        """
        Return a new QueryParams instance, setting or appending the value of a key.

        Usage:

        ```
        q = httpx.QueryParams("a=123")
        q = q.add("a", "456")
        assert q == httpx.QueryParams("a=123&a=456")
        ```
        """

    def remove(self, key: str) -> QueryParams:
        """
        Return a new QueryParams instance, removing the value of a key.

        Usage:
        ```
        q = httpx.QueryParams("a=123")
        q = q.remove("a")
        assert q == httpx.QueryParams("")
        ```
        """

    def merge(self, params: QueryParamTypes | None = None) -> QueryParams:
        """
        Return a new QueryParams instance, updated with.

        Usage:
        ```
        q = httpx.QueryParams("a=123")
        q = q.merge({"b": "456"})
        assert q == httpx.QueryParams("a=123&b=456")

        q = httpx.QueryParams("a=123")
        q = q.merge({"a": "456", "b": "789"})
        assert q == httpx.QueryParams("a=456&b=789")
        ```
        """

    def __getitem__(self, key: typing.Any) -> str:...
    def __contains__(self, key: typing.Any) -> bool:...
    def __iter__(self) -> typing.Iterator[typing.Any]:...
    def __len__(self) -> int:...
    def __bool__(self) -> bool:...
    def __hash__(self) -> int:...
    def __eq__(self, other: typing.Any) -> bool:...
    def __str__(self) -> str:...
    def __repr__(self) -> str:...
    def update(self, params: QueryParamTypes | None = None) -> None:...
    def __setitem__(self, key: str, value: str) -> None:...


def normalize_path(path: str) -> str:
    """
    Drop "." and ".." segments from a URL path.

    For example:

        normalize_path("/path/./to/somewhere/..") == "/path/to"
    """

def quote(string: str, safe: str) -> str:
    """
    Use percent-encoding to quote a string, omitting existing '%xx' escape sequences.

    See: https://www.rfc-editor.org/rfc/rfc3986#section-2.1

    * `string`: The string to be percent-escaped.
    * `safe`: A string containing characters that may be treated as safe, and do not
        need to be escaped. Unreserved characters are always treated as safe.
        See: https://www.rfc-editor.org/rfc/rfc3986#section-2.3
    """
