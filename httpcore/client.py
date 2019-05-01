import typing
from types import TracebackType

from .adapters.authentication import AuthenticationAdapter
from .adapters.cookies import CookieAdapter
from .adapters.environment import EnvironmentAdapter
from .adapters.redirects import RedirectAdapter
from .config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from .dispatch.connection_pool import ConnectionPool
from .models import URL, ByteOrByteStream, HeaderTypes, Request, Response, URLTypes


class Client:
    def __init__(
        self,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ):
        connection_pool = ConnectionPool(
            ssl=ssl, timeout=timeout, pool_limits=pool_limits
        )
        cookie_adapter = CookieAdapter(dispatch=connection_pool)
        auth_adapter = AuthenticationAdapter(dispatch=cookie_adapter)
        redirect_adapter = RedirectAdapter(
            dispatch=auth_adapter, max_redirects=max_redirects
        )
        self.adapter = EnvironmentAdapter(dispatch=redirect_adapter)

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: ByteOrByteStream = b"",
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        request = Request(method, url, headers=headers, content=content)
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
        url: URLTypes,
        *,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "GET",
            url,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def options(
        self,
        url: URLTypes,
        *,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "OPTIONS",
            url,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def head(
        self,
        url: URLTypes,
        *,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "HEAD",
            url,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def post(
        self,
        url: URLTypes,
        *,
        content: ByteOrByteStream = b"",
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "POST",
            url,
            content=content,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def put(
        self,
        url: URLTypes,
        *,
        content: ByteOrByteStream = b"",
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "PUT",
            url,
            content=content,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def patch(
        self,
        url: URLTypes,
        *,
        content: ByteOrByteStream = b"",
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "PATCH",
            url,
            content=content,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def delete(
        self,
        url: URLTypes,
        *,
        content: ByteOrByteStream = b"",
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "DELETE",
            url,
            content=content,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
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
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        options = {
            "stream": stream,
            "allow_redirects": allow_redirects,
        }  # type: typing.Dict[str, typing.Any]

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
