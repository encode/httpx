import typing
from types import TracebackType

from .auth import AuthAdapter
from .config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from .connection_pool import ConnectionPool
from .cookies import CookieAdapter
from .environment import EnvironmentAdapter
from .models import URL, Request, Response
from .redirects import RedirectAdapter


class Client:
    def __init__(
        self,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ):
        connection_pool = ConnectionPool(ssl=ssl, timeout=timeout, limits=limits)
        cookie_adapter = CookieAdapter(dispatch=connection_pool)
        auth_adapter = AuthAdapter(dispatch=cookie_adapter)
        redirect_adapter = RedirectAdapter(
            dispatch=auth_adapter, max_redirects=max_redirects
        )
        self.adapter = EnvironmentAdapter(dispatch=redirect_adapter)

    async def request(
        self,
        method: str,
        url: typing.Union[str, URL],
        *,
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        headers: typing.List[typing.Tuple[bytes, bytes]] = [],
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        request = Request(method, url, headers=headers, body=body)
        self.prepare_request(request)
        response = await self.send(
            request,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )
        return response

    async def get(
        self,
        url: typing.Union[str, URL],
        *,
        headers: typing.List[typing.Tuple[bytes, bytes]] = [],
        stream: bool = False,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        return await self.request(
            "GET", url, headers=headers, stream=stream, ssl=ssl, timeout=timeout
        )

    async def post(
        self,
        url: typing.Union[str, URL],
        *,
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        headers: typing.List[typing.Tuple[bytes, bytes]] = [],
        stream: bool = False,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        return await self.request(
            "POST",
            url,
            body=body,
            headers=headers,
            stream=stream,
            ssl=ssl,
            timeout=timeout,
        )

    def prepare_request(self, request: Request) -> None:
        self.adapter.prepare_request(request)

    async def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        options = {"stream": stream}  # type: typing.Dict[str, typing.Any]
        if ssl is not None:
            options["ssl"] = ssl
        if timeout is not None:
            options["timeout"] = timeout
        return await self.adapter.send(request, **options)

    async def close(self) -> None:
        await self.adapter.close()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()
