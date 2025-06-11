class ParseResult:
    scheme: str
    userinfo: str
    host: str
    port: int | None
    path: str
    query: str | None
    fragment: str | None

    @property
    def authority(self) -> str: ...
    @property
    def netloc(self) -> str: ...
    def __str__(self) -> str: ...
    def __new__(
        cls,
        scheme: str,
        userinfo: str,
        host: str,
        port: int | None,
        path: str,
        query: str | None,
        fragment: str | None,
    ) -> ParseResult: ...
