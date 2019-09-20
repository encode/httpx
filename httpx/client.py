import functools
import inspect
import typing
from types import TracebackType

import hstspreload

from .concurrency.asyncio import AsyncioBackend
from .concurrency.base import ConcurrencyBackend
from .config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    HTTPVersionTypes,
    PoolLimits,
    TimeoutTypes,
    VerifyTypes,
)
from .dispatch.asgi import ASGIDispatch
from .dispatch.base import AsyncDispatcher, Dispatcher
from .dispatch.connection_pool import ConnectionPool
from .dispatch.proxy_http import HTTPProxy
from .dispatch.threaded import ThreadedDispatcher
from .dispatch.wsgi import WSGIDispatch
from .exceptions import HTTPError, InvalidURL
from .middleware.base import BaseMiddleware
from .middleware.basic_auth import BasicAuthMiddleware
from .middleware.custom_auth import CustomAuthMiddleware
from .middleware.redirect import RedirectMiddleware
from .models import (
    URL,
    AsyncRequest,
    AsyncRequestData,
    AsyncResponse,
    AsyncResponseContent,
    AuthTypes,
    Cookies,
    CookieTypes,
    Headers,
    HeaderTypes,
    ProxiesTypes,
    QueryParamTypes,
    RequestData,
    RequestFiles,
    Response,
    ResponseContent,
    URLTypes,
)
from .utils import ElapsedTimer, get_environment_proxies, get_netrc_login


class BaseClient:
    def __init__(
        self,
        *,
        auth: AuthTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http_versions: HTTPVersionTypes = None,
        proxies: ProxiesTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        base_url: URLTypes = None,
        dispatch: typing.Union[AsyncDispatcher, Dispatcher] = None,
        app: typing.Callable = None,
        backend: ConcurrencyBackend = None,
        trust_env: bool = True,
    ):
        if backend is None:
            backend = AsyncioBackend()

        self.check_concurrency_backend(backend)

        if app is not None:
            param_count = len(inspect.signature(app).parameters)
            assert param_count in (2, 3)
            if param_count == 2:
                dispatch = WSGIDispatch(app=app)
            else:
                dispatch = ASGIDispatch(app=app)

        self.trust_env = True if trust_env is None else trust_env

        if dispatch is None:
            async_dispatch: AsyncDispatcher = ConnectionPool(
                verify=verify,
                cert=cert,
                timeout=timeout,
                http_versions=http_versions,
                pool_limits=pool_limits,
                backend=backend,
                trust_env=self.trust_env,
            )
        elif isinstance(dispatch, Dispatcher):
            async_dispatch = ThreadedDispatcher(dispatch, backend)
        else:
            async_dispatch = dispatch

        if base_url is None:
            self.base_url = URL("", allow_relative=True)
        else:
            self.base_url = URL(base_url)

        if proxies is None and trust_env:
            proxies = typing.cast(ProxiesTypes, get_environment_proxies())

        self.proxies: typing.Dict[str, AsyncDispatcher] = _proxies_to_dispatchers(
            proxies
        )

        self.auth = auth
        self._headers = Headers(headers)
        self._cookies = Cookies(cookies)
        self.max_redirects = max_redirects
        self.dispatch = async_dispatch
        self.concurrency_backend = backend

    @property
    def headers(self) -> Headers:
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTypes) -> None:
        self._headers = Headers(headers)

    @property
    def cookies(self) -> Cookies:
        return self._cookies

    @cookies.setter
    def cookies(self, cookies: CookieTypes) -> None:
        self._cookies = Cookies(cookies)

    def check_concurrency_backend(self, backend: ConcurrencyBackend) -> None:
        pass  # pragma: no cover

    def merge_url(self, url: URLTypes) -> URL:
        url = self.base_url.join(relative_url=url)
        if url.scheme == "http" and hstspreload.in_hsts_preload(url.host):
            url = url.copy_with(scheme="https")
        return url

    def merge_cookies(
        self, cookies: CookieTypes = None
    ) -> typing.Optional[CookieTypes]:
        if cookies or self.cookies:
            merged_cookies = Cookies(self.cookies)
            merged_cookies.update(cookies)
            return merged_cookies
        return cookies

    def merge_headers(
        self, headers: HeaderTypes = None
    ) -> typing.Optional[HeaderTypes]:
        if headers or self.headers:
            merged_headers = Headers(self.headers)
            merged_headers.update(headers)
            return merged_headers
        return headers

    async def _get_response(
        self,
        request: AsyncRequest,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        if request.url.scheme not in ("http", "https"):
            raise InvalidURL('URL scheme must be "http" or "https".')

        if proxies is not None:
            dispatch_proxies = _proxies_to_dispatchers(proxies)
        else:
            dispatch_proxies = self.proxies
        dispatch = self._dispatcher_for_request(request, dispatch_proxies)

        async def get_response(request: AsyncRequest) -> AsyncResponse:
            try:
                with ElapsedTimer() as timer:
                    response = await dispatch.send(
                        request, verify=verify, cert=cert, timeout=timeout
                    )
                response.elapsed = timer.elapsed
            except HTTPError as exc:
                # Add the original request to any HTTPError unless
                # there'a already a request attached in the case of
                # a ProxyError.
                if exc.request is None:
                    exc.request = request
                raise

            self.cookies.extract_cookies(response)
            if not stream:
                try:
                    await response.read()
                finally:
                    await response.close()

            return response

        def wrap(
            get_response: typing.Callable, middleware: BaseMiddleware
        ) -> typing.Callable:
            return functools.partial(middleware, get_response=get_response)

        get_response = wrap(
            get_response,
            RedirectMiddleware(allow_redirects=allow_redirects, cookies=self.cookies),
        )

        auth_middleware = self._get_auth_middleware(
            request=request,
            trust_env=self.trust_env if trust_env is None else trust_env,
            auth=self.auth if auth is None else auth,
        )

        if auth_middleware is not None:
            get_response = wrap(get_response, auth_middleware)

        return await get_response(request)

    def _get_auth_middleware(
        self, request: AsyncRequest, trust_env: bool, auth: AuthTypes = None
    ) -> typing.Optional[BaseMiddleware]:
        if isinstance(auth, tuple):
            return BasicAuthMiddleware(username=auth[0], password=auth[1])
        elif isinstance(auth, BaseMiddleware):
            return auth
        elif callable(auth):
            return CustomAuthMiddleware(auth=auth)

        if auth is not None:
            raise TypeError(
                'When specified, "auth" must be a (username, password) tuple or '
                "a callable with signature (AsyncRequest) -> AsyncRequest "
                f"(got {auth!r})"
            )

        if request.url.username or request.url.password:
            return BasicAuthMiddleware(
                username=request.url.username, password=request.url.password
            )

        if trust_env:
            netrc_login = get_netrc_login(request.url.authority)
            if netrc_login:
                username, _, password = netrc_login
                return BasicAuthMiddleware(username=username, password=password)

        return None

    def _dispatcher_for_request(
        self, request: AsyncRequest, proxies: typing.Dict[str, AsyncDispatcher]
    ) -> AsyncDispatcher:
        """Gets the AsyncDispatcher instance that should be used for a given Request"""
        if proxies:
            url = request.url
            is_default_port = (url.scheme == "http" and url.port == 80) or (
                url.scheme == "https" and url.port == 443
            )
            hostname = f"{url.host}:{url.port}"
            proxy_keys = (
                f"{url.scheme}://{hostname}",
                f"{url.scheme}://{url.host}" if is_default_port else None,
                f"all://{hostname}",
                f"all://{url.host}" if is_default_port else None,
                url.scheme,
                "all",
            )
            for proxy_key in proxy_keys:
                if proxy_key and proxy_key in proxies:
                    dispatcher = proxies[proxy_key]
                    return dispatcher

        return self.dispatch

    def build_request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: AsyncRequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
    ) -> AsyncRequest:
        url = self.merge_url(url)
        headers = self.merge_headers(headers)
        cookies = self.merge_cookies(cookies)
        request = AsyncRequest(
            method,
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        return request


class AsyncClient(BaseClient):
    async def get(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def options(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def head(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = False,  # NOTE: Differs to usual default.
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def post(
        self,
        url: URLTypes,
        *,
        data: AsyncRequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "POST",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def put(
        self,
        url: URLTypes,
        *,
        data: AsyncRequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "PUT",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def patch(
        self,
        url: URLTypes,
        *,
        data: AsyncRequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "PATCH",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def delete(
        self,
        url: URLTypes,
        *,
        data: AsyncRequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self.request(
            "DELETE",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: AsyncRequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        request = self.build_request(
            method=method,
            url=url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        response = await self.send(
            request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )
        return response

    async def send(
        self,
        request: AsyncRequest,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> AsyncResponse:
        return await self._get_response(
            request=request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    async def close(self) -> None:
        await self.dispatch.close()

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()


class Client(BaseClient):
    def check_concurrency_backend(self, backend: ConcurrencyBackend) -> None:
        # Iterating over response content allocates an async environment on each step.
        # This is relatively cheap on asyncio, but cannot be guaranteed for all
        # concurrency backends.
        # The sync client performs I/O on its own, so it doesn't need to support
        # arbitrary concurrency backends.
        # Therefore, we keep the `backend` parameter (for testing/mocking), but require
        # that the concurrency backend relies on asyncio.

        if isinstance(backend, AsyncioBackend):
            return

        if hasattr(backend, "loop"):
            # Most likely a proxy class.
            return

        raise ValueError("'Client' only supports asyncio-based concurrency backends")

    def _async_request_data(
        self, data: RequestData = None
    ) -> typing.Optional[AsyncRequestData]:
        """
        If the request data is an bytes iterator then return an async bytes
        iterator onto the request data.
        """
        if data is None or isinstance(data, (str, bytes, dict)):
            return data

        # Coerce an iterator into an async iterator, with each item in the
        # iteration running as a thread-pooled operation.
        assert hasattr(data, "__iter__")
        return self.concurrency_backend.iterate_in_threadpool(data)

    def _sync_data(self, data: AsyncResponseContent) -> ResponseContent:
        if isinstance(data, bytes):
            return data

        # Coerce an async iterator into an iterator, with each item in the
        # iteration run within the event loop.
        assert hasattr(data, "__aiter__")
        return self.concurrency_backend.iterate(data)

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        request = self.build_request(
            method=method,
            url=url,
            data=self._async_request_data(data),
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        response = self.send(
            request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )
        return response

    def send(
        self,
        request: AsyncRequest,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        concurrency_backend = self.concurrency_backend

        coroutine = self._get_response
        args = [request]
        kwargs = {
            "stream": True,
            "auth": auth,
            "allow_redirects": allow_redirects,
            "verify": verify,
            "cert": cert,
            "timeout": timeout,
            "trust_env": trust_env,
            "proxies": proxies,
        }
        async_response = concurrency_backend.run(coroutine, *args, **kwargs)

        content = getattr(
            async_response, "_raw_content", getattr(async_response, "_raw_stream", None)
        )

        sync_content = self._sync_data(content)

        def sync_on_close() -> None:
            nonlocal concurrency_backend, async_response
            concurrency_backend.run(async_response.on_close)

        response = Response(
            status_code=async_response.status_code,
            http_version=async_response.http_version,
            headers=async_response.headers,
            content=sync_content,
            on_close=sync_on_close,
            request=async_response.request,
            history=async_response.history,
            elapsed=async_response.elapsed,
        )
        if not stream:
            try:
                response.read()
            finally:
                response.close()
        return response

    def get(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def options(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def head(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = False,  # NOTE: Differs to usual default.
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def post(
        self,
        url: URLTypes,
        *,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "POST",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def put(
        self,
        url: URLTypes,
        *,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "PUT",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def patch(
        self,
        url: URLTypes,
        *,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "PATCH",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def delete(
        self,
        url: URLTypes,
        *,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
        proxies: ProxiesTypes = None,
    ) -> Response:
        return self.request(
            "DELETE",
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
            proxies=proxies,
        )

    def close(self) -> None:
        coroutine = self.dispatch.close
        self.concurrency_backend.run(coroutine)

    def __enter__(self) -> "Client":
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()


def _proxy_from_url(url: URLTypes) -> AsyncDispatcher:
    url = URL(url)
    if url.scheme in ("http", "https"):
        return HTTPProxy(url)
    raise ValueError(f"Unknown proxy for {url!r}")


def _proxies_to_dispatchers(
    proxies: typing.Optional[ProxiesTypes]
) -> typing.Dict[str, AsyncDispatcher]:
    if proxies is None:
        return {}
    elif isinstance(proxies, (str, URL)):
        return {"all": _proxy_from_url(proxies)}
    elif isinstance(proxies, AsyncDispatcher):
        return {"all": proxies}
    else:
        new_proxies = {}
        for key, dispatcher_or_url in proxies.items():
            if isinstance(dispatcher_or_url, (str, URL)):
                new_proxies[str(key)] = _proxy_from_url(dispatcher_or_url)
            else:
                new_proxies[str(key)] = dispatcher_or_url
        return new_proxies
