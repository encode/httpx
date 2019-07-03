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
    Request,
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
        self.cookies = Cookies(cookies)
        self.max_redirects = max_redirects
        self.dispatch = async_dispatch
        self.concurrency_backend = backend

    def merge_cookies(
        self, cookies: CookieTypes = None
    ) -> typing.Optional[CookieTypes]:
        if cookies or self.cookies:
            merged_cookies = Cookies(self.cookies)
            merged_cookies.update(cookies)
            return merged_cookies
        return cookies

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
        if auth is None:
            auth = self.auth

        url = request.url

        if url.scheme not in ("http", "https"):
            raise InvalidURL('URL scheme must be "http" or "https".')

        if auth is None and (url.username or url.password):
            auth = HTTPBasicAuth(username=url.username, password=url.password)

        if auth is not None:
            if isinstance(auth, tuple):
                auth = HTTPBasicAuth(username=auth[0], password=auth[1])
            request = auth(request)

        response = await self.send_handling_redirects(
            request,
            verify=verify,
            cert=cert,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )

        if not stream:
            try:
                await response.read()
            finally:
                await response.close()

        return response

    async def send_handling_redirects(
        self,
        request: AsyncRequest,
        *,
        cert: CertTypes = None,
        verify: VerifyTypes = None,
        timeout: TimeoutTypes = None,
        allow_redirects: bool = True,
        history: typing.List[AsyncResponse] = None,
    ) -> AsyncResponse:
        if history is None:
            history = []

        while True:
            # We perform these checks here, so that calls to `response.next()`
            # will raise redirect errors if appropriate.
            if len(history) > self.max_redirects:
                raise TooManyRedirects()
            if request.url in [response.url for response in history]:
                raise RedirectLoop()

            response = await self.dispatch.send(
                request, verify=verify, cert=cert, timeout=timeout
            )
            should_close_response = True
            try:
                assert isinstance(response, AsyncResponse)
                response.history = list(history)
                self.cookies.extract_cookies(response)
                history = history + [response]

                if allow_redirects and response.is_redirect:
                    request = self.build_redirect_request(request, response)
                else:
                    should_close_response = False
                    break
            finally:
                if should_close_response:
                    await response.close()

        if response.is_redirect:

            async def send_next() -> AsyncResponse:
                nonlocal request, response, verify, cert, allow_redirects, timeout, history
                request = self.build_redirect_request(request, response)
                response = await self.send_handling_redirects(
                    request,
                    allow_redirects=allow_redirects,
                    verify=verify,
                    cert=cert,
                    timeout=timeout,
                    history=history,
                )
                return response

            response.next = send_next  # type: ignore

        return response

    def build_redirect_request(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> AsyncRequest:
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url)
        content = self.redirect_content(request, method)
        cookies = self.merge_cookies(request.cookies)
        return AsyncRequest(
            method=method, url=url, headers=headers, data=content, cookies=cookies
        )

    def redirect_method(self, request: AsyncRequest, response: AsyncResponse) -> str:
        """
        When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.SEE_OTHER and method != "HEAD":
            method = "GET"

        # Do what the browsers do, despite standards...
        # Turn 302s into GETs.
        if response.status_code == codes.FOUND and method != "HEAD":
            method = "GET"

        # If a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in 'requests' issue 1704.
        if response.status_code == codes.MOVED_PERMANENTLY and method == "POST":
            method = "GET"

        return method

    def redirect_url(self, request: AsyncRequest, response: AsyncResponse) -> URL:
        """
        Return the URL for the redirect to follow.
        """
        location = response.headers["Location"]

        url = URL(location, allow_relative=True)

        # Facilitate relative 'Location' headers, as allowed by RFC 7231.
        # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
        if url.is_relative_url:
            url = request.url.join(url)

        # Attach previous fragment if needed (RFC 7231 7.1.2)
        if request.url.fragment and not url.fragment:
            url = url.copy_with(fragment=request.url.fragment)

        return url

    def redirect_headers(self, request: AsyncRequest, url: URL) -> Headers:
        """
        Strip Authorization headers when responses are redirected away from
        the origin.
        """
        headers = Headers(request.headers)
        if url.origin != request.url.origin:
            del headers["Authorization"]
        return headers

    def redirect_content(self, request: AsyncRequest, method: str) -> bytes:
        """
        Return the body that should be used for the redirect request.
        """
        if method != request.method and method == "GET":
            return b""
        if request.is_streaming:
            raise RedirectBodyUnavailable()
        return request.content


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
        kwargs = dict(
            stream=True,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
        )
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
