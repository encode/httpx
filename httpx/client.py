import inspect
import typing
from types import TracebackType

from .auth import HTTPBasicAuth
from .concurrency import AsyncioBackend
from .config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    PoolLimits,
    TimeoutTypes,
    VerifyTypes,
)
from .dispatch.asgi import ASGIDispatch
from .dispatch.connection_pool import ConnectionPool
from .dispatch.threaded import ThreadedDispatcher
from .dispatch.wsgi import WSGIDispatch
from .exceptions import (
    InvalidURL,
    RedirectBodyUnavailable,
    RedirectLoop,
    TooManyRedirects,
)
from .interfaces import AsyncDispatcher, ConcurrencyBackend, Dispatcher
from .middlewares import (
    BaseMiddleware,
    RedirectMiddleware,
    HTTPBasicAuthMiddleware,
)
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
    QueryParamTypes,
    RequestData,
    RequestFiles,
    Response,
    ResponseContent,
    URLTypes,
)
from .status_codes import codes


class BaseClient:
    def __init__(
        self,
        auth: AuthTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        base_url: URLTypes = None,
        dispatch: typing.Union[AsyncDispatcher, Dispatcher] = None,
        app: typing.Callable = None,
        raise_app_exceptions: bool = True,
        backend: ConcurrencyBackend = None,
        additional_middlewares: list = None,  # TODO: is this the best way to inject mws?
    ):
        if backend is None:
            backend = AsyncioBackend()

        if app is not None:
            param_count = len(inspect.signature(app).parameters)
            assert param_count in (2, 3)
            if param_count == 2:
                dispatch = WSGIDispatch(
                    app=app, raise_app_exceptions=raise_app_exceptions
                )
            else:
                dispatch = ASGIDispatch(
                    app=app, raise_app_exceptions=raise_app_exceptions
                )

        if dispatch is None:
            async_dispatch = ConnectionPool(
                verify=verify,
                cert=cert,
                timeout=timeout,
                pool_limits=pool_limits,
                backend=backend,
            )  # type: AsyncDispatcher
        elif isinstance(dispatch, Dispatcher):
            async_dispatch = ThreadedDispatcher(dispatch, backend)
        else:
            async_dispatch = dispatch

        if base_url is None:
            self.base_url = URL("", allow_relative=True)
        else:
            self.base_url = URL(base_url)

        self.auth = auth
        self.headers = Headers(headers)
        self.cookies = Cookies(cookies)
        self.max_redirects = max_redirects
        self.dispatch = async_dispatch
        self.concurrency_backend = backend
        self.additional_middlewares = additional_middlewares or []

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
    ) -> AsyncResponse:
        url = request.url
        if url.scheme not in ("http", "https"):
            raise InvalidURL('URL scheme must be "http" or "https".')

        middlewares: typing.List[BaseMiddleware] = [
            # TODO: RedirectMW uses a combination of parameters to the client
            # but also to send, which makes this awkward instantiation
            RedirectMiddleware(
                allow_redirects=allow_redirects,
                max_redirects=self.max_redirects,
                base_cookies=self.cookies,
            ),
        ]

        if auth is None and (url.username or url.password):
            middlewares.append(HTTPBasicAuthMiddleware(username=url.username, password=url.password))
        elif isinstance(auth, tuple):
            middlewares.append(HTTPBasicAuthMiddleware(username=auth[0], password=auth[1]))
        elif isinstance(auth, HTTPBasicAuth):
            middlewares.append(HTTPBasicAuthMiddleware(username=auth.username, password=auth.password))

        middlewares.extend(self.additional_middlewares)

        while True:
            for middleware in middlewares:
                request = middleware.process_request(request)

            response = await self.dispatch.send(
                request, verify=verify, cert=cert, timeout=timeout
            )

            for middleware in middlewares:
                result = middleware.process_response(request, response)
                if isinstance(result, AsyncRequest):
                    request = result
                    break  # do not process more middlewares as one has an action to take

            if isinstance(result, AsyncResponse):
                break  # we have a response after all middlewares have processed the result

        if not stream:
            try:
                await response.read()
            finally:
                await response.close()

        return response


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
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
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
    ) -> AsyncResponse:
        url = self.base_url.join(url)
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
        response = await self.send(
            request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
        )
        return response

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
    ) -> Response:
        url = self.base_url.join(url)
        headers = self.merge_headers(headers)
        cookies = self.merge_cookies(cookies)
        request = AsyncRequest(
            method,
            url,
            data=self._async_request_data(data),
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        concurrency_backend = self.concurrency_backend

        coroutine = self.send
        args = [request]
        kwargs = {
            "stream": True,
            "auth": auth,
            "allow_redirects": allow_redirects,
            "verify": verify,
            "cert": cert,
            "timeout": timeout,
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
            protocol=async_response.protocol,
            headers=async_response.headers,
            content=sync_content,
            on_close=sync_on_close,
            request=async_response.request,
            history=async_response.history,
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
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
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
