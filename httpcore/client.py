import asyncio
import typing
from types import TracebackType

from .auth import HTTPBasicAuth
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
from .exceptions import RedirectBodyUnavailable, RedirectLoop, TooManyRedirects
from .interfaces import ConcurrencyBackend, Dispatcher
from .models import (
    URL,
    AuthTypes,
    Headers,
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    SyncResponse,
    URLTypes,
)
from .status_codes import codes


class AsyncClient:
    def __init__(
        self,
        auth: AuthTypes = None,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        dispatch: Dispatcher = None,
        backend: ConcurrencyBackend = None,
    ):
        if dispatch is None:
            dispatch = ConnectionPool(
                ssl=ssl, timeout=timeout, pool_limits=pool_limits, backend=backend
            )

        self.auth = auth
        self.max_redirects = max_redirects
        self.dispatch = dispatch

    async def get(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "GET",
            url,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def options(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "OPTIONS",
            url,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def head(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "HEAD",
            url,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def post(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "POST",
            url,
            data=data,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def put(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "PUT",
            url,
            data=data,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def patch(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "PATCH",
            url,
            data=data,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def delete(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        return await self.request(
            "DELETE",
            url,
            data=data,
            query_params=query_params,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        request = Request(
            method, url, data=data, query_params=query_params, headers=headers
        )
        self.prepare_request(request)
        response = await self.send(
            request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )
        return response

    def prepare_request(self, request: Request) -> None:
        request.prepare()

    async def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
        allow_redirects: bool = True,
    ) -> Response:
        if auth is None:
            auth = self.auth

        url = request.url
        if auth is None and (url.username or url.password):
            auth = HTTPBasicAuth(username=url.username, password=url.password)

        if auth is not None:
            if isinstance(auth, tuple):
                auth = HTTPBasicAuth(username=auth[0], password=auth[1])
            request = auth(request)

        response = await self.send_handling_redirects(
            request,
            stream=stream,
            ssl=ssl,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
        return response

    async def send_handling_redirects(
        self,
        request: Request,
        *,
        stream: bool = False,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
        allow_redirects: bool = True,
        history: typing.List[Response] = None,
    ) -> Response:
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
                request, stream=stream, ssl=ssl, timeout=timeout
            )
            response.history = list(history)
            history = [response] + history
            if not response.is_redirect:
                break

            if allow_redirects:
                request = self.build_redirect_request(request, response)
            else:

                async def send_next() -> Response:
                    nonlocal request, response, ssl, allow_redirects, timeout, history
                    request = self.build_redirect_request(request, response)
                    response = await self.send_handling_redirects(
                        request,
                        stream=stream,
                        allow_redirects=allow_redirects,
                        ssl=ssl,
                        timeout=timeout,
                        history=history,
                    )
                    return response

                response.next = send_next  # type: ignore
                break

        return response

    def build_redirect_request(self, request: Request, response: Response) -> Request:
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url)
        content = self.redirect_content(request, method)
        return Request(method=method, url=url, headers=headers, data=content)

    def redirect_method(self, request: Request, response: Response) -> str:
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

    def redirect_url(self, request: Request, response: Response) -> URL:
        """
        Return the URL for the redirect to follow.
        """
        location = response.headers["Location"]

        url = URL(location, allow_relative=True)

        # Facilitate relative 'Location' headers, as allowed by RFC 7231.
        # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
        if url.is_relative_url:
            url = url.resolve_with(request.url)

        # Attach previous fragment if needed (RFC 7231 7.1.2)
        if request.url.fragment and not url.fragment:
            url = url.copy_with(fragment=request.url.fragment)

        return url

    def redirect_headers(self, request: Request, url: URL) -> Headers:
        """
        Strip Authorization headers when responses are redirected away from
        the origin.
        """
        headers = Headers(request.headers)
        if url.origin != request.url.origin:
            del headers["Authorization"]
        return headers

    def redirect_content(self, request: Request, method: str) -> bytes:
        """
        Return the body that should be used for the redirect request.
        """
        if method != request.method and method == "GET":
            return b""
        if request.is_streaming:
            raise RedirectBodyUnavailable()
        return request.content

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


class Client:
    def __init__(
        self,
        auth: AuthTypes = None,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        dispatch: Dispatcher = None,
        backend: ConcurrencyBackend = None,
    ) -> None:
        self._client = AsyncClient(
            auth=auth,
            ssl=ssl,
            timeout=timeout,
            pool_limits=pool_limits,
            max_redirects=max_redirects,
            dispatch=dispatch,
            backend=backend,
        )
        self._loop = asyncio.new_event_loop()

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        request = Request(
            method, url, data=data, query_params=query_params, headers=headers
        )
        self.prepare_request(request)
        response = self.send(
            request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )
        return response

    def get(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "GET",
            url,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def options(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "OPTIONS",
            url,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def head(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "HEAD",
            url,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def post(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "POST",
            url,
            data=data,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def put(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "PUT",
            url,
            data=data,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def patch(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "PATCH",
            url,
            data=data,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def delete(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "DELETE",
            url,
            data=data,
            headers=headers,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def prepare_request(self, request: Request) -> None:
        self._client.prepare_request(request)

    def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        response = self._loop.run_until_complete(
            self._client.send(
                request,
                stream=stream,
                auth=auth,
                allow_redirects=allow_redirects,
                ssl=ssl,
                timeout=timeout,
            )
        )
        return SyncResponse(response, self._loop)

    def close(self) -> None:
        self._loop.run_until_complete(self._client.close())

    def __enter__(self) -> "Client":
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()
