import functools
import netrc
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
from .dispatch.base import Dispatcher
from .dispatch.connection_pool import ConnectionPool
from .dispatch.proxy_http import HTTPProxy
from .exceptions import HTTPError, InvalidURL
from .middleware.base import BaseMiddleware
from .middleware.basic_auth import BasicAuthMiddleware
from .middleware.custom_auth import CustomAuthMiddleware
from .middleware.redirect import RedirectMiddleware
from .models import (
    URL,
    AuthTypes,
    Cookies,
    CookieTypes,
    Headers,
    HeaderTypes,
    ProxiesTypes,
    QueryParams,
    QueryParamTypes,
    Request,
    RequestData,
    RequestFiles,
    Response,
    URLTypes,
)
from .utils import ElapsedTimer, get_environment_proxies, get_logger, get_netrc

logger = get_logger(__name__)


class Client:
    """
    An HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc.

    Usage:

    ```
    >>> client = httpx.Client()
    >>> response = client.get('https://example.org')
    ```

    **Parameters:**

    * **auth** - *(optional)* An authentication class to use when sending
    requests.
    * **params** - *(optional)* Query parameters to include in request URLs, as
    a string, dictionary, or list of two-tuples.
    * **headers** - *(optional)* Dictionary of HTTP headers to include when
    sending requests.
    * **cookies** - *(optional)* Dictionary of Cookie items to include when
    sending requests.
    * **verify** - *(optional)* SSL certificates (a.k.a CA bundle) used to
    verify the identity of requested hosts. Either `True` (default CA bundle),
    a path to an SSL certificate file, or `False` (disable verification).
    * **cert** - *(optional)* An SSL certificate used by the requested host
    to authenticate the client. Either a path to an SSL certificate file, or
    two-tuple of (certificate file, key file), or a three-tuple of (certificate
    file, key file, password).
    * **http_versions** - *(optional)* A list of strings of HTTP protocol
    versions to use when sending requests. eg. `http_versions=["HTTP/1.1"]`
    * **proxies** - *(optional)* A dictionary mapping HTTP protocols to proxy
    URLs.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    requests.
    * **pool_limits** - *(optional)* The connection pool configuration to use
    when determining the maximum number of concurrently open HTTP connections.
    * **max_redirects** - *(optional)* The maximum number of redirect responses
    that should be followed.
    * **base_url** - *(optional)* A URL to use as the base when building
    request URLs.
    * **dispatch** - *(optional)* A dispatch class to use for sending requests
    over the network.
    * **app** - *(optional)* An ASGI application to send requests to,
    rather than sending actual network requests.
    * **backend** - *(optional)* A concurrency backend to use when issuing
    async requests.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.
    * **uds** - *(optional)* A path to a Unix domain socket to connect through.
    """

    def __init__(
        self,
        *,
        auth: AuthTypes = None,
        params: QueryParamTypes = None,
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
        dispatch: Dispatcher = None,
        app: typing.Callable = None,
        backend: ConcurrencyBackend = None,
        trust_env: bool = True,
        uds: str = None,
    ):
        if backend is None:
            backend = AsyncioBackend()

        if app is not None:
            dispatch = ASGIDispatch(app=app, backend=backend)

        self.trust_env = True if trust_env is None else trust_env

        if dispatch is None:
            dispatch = ConnectionPool(
                verify=verify,
                cert=cert,
                timeout=timeout,
                http_versions=http_versions,
                pool_limits=pool_limits,
                backend=backend,
                trust_env=self.trust_env,
                uds=uds,
            )

        if base_url is None:
            self.base_url = URL("", allow_relative=True)
        else:
            self.base_url = URL(base_url)

        if params is None:
            params = {}

        self.auth = auth
        self._params = QueryParams(params)
        self._headers = Headers(headers)
        self._cookies = Cookies(cookies)
        self.max_redirects = max_redirects
        self.dispatch = dispatch
        self.concurrency_backend = backend

        if proxies is None and trust_env:
            proxies = typing.cast(ProxiesTypes, get_environment_proxies())

        self.proxies: typing.Dict[str, Dispatcher] = _proxies_to_dispatchers(
            proxies,
            verify=verify,
            cert=cert,
            timeout=timeout,
            http_versions=http_versions,
            pool_limits=pool_limits,
            backend=backend,
            trust_env=trust_env,
        )

    @property
    def headers(self) -> Headers:
        """
        HTTP headers to include when sending requests.
        """
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTypes) -> None:
        self._headers = Headers(headers)

    @property
    def cookies(self) -> Cookies:
        """
        Cookie values to include when sending requests.
        """
        return self._cookies

    @cookies.setter
    def cookies(self, cookies: CookieTypes) -> None:
        self._cookies = Cookies(cookies)

    @property
    def params(self) -> QueryParams:
        """
        Query parameters to include in the URL when sending requests.
        """
        return self._params

    @params.setter
    def params(self, params: QueryParamTypes) -> None:
        self._params = QueryParams(params)

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

    def merge_queryparams(
        self, params: QueryParamTypes = None
    ) -> typing.Optional[QueryParamTypes]:
        if params or self.params:
            merged_queryparams = QueryParams(self.params)
            merged_queryparams.update(params)
            return merged_queryparams
        return params

    async def _get_response(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
    ) -> Response:
        if request.url.scheme not in ("http", "https"):
            raise InvalidURL('URL scheme must be "http" or "https".')

        dispatch = self._dispatcher_for_request(request, self.proxies)

        async def get_response(request: Request) -> Response:
            try:
                with ElapsedTimer() as timer:
                    response = await dispatch.send(
                        request, verify=verify, cert=cert, timeout=timeout
                    )
                response.elapsed = timer.elapsed
                response.request = request
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

            status = f"{response.status_code} {response.reason_phrase}"
            response_line = f"{response.http_version} {status}"
            logger.debug(
                f'HTTP Request: {request.method} {request.url} "{response_line}"'
            )

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
        self, request: Request, trust_env: bool, auth: AuthTypes = None
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
                "a callable with signature (Request) -> Request "
                f"(got {auth!r})"
            )

        if request.url.username or request.url.password:
            return BasicAuthMiddleware(
                username=request.url.username, password=request.url.password
            )

        if trust_env:
            netrc_info = self._get_netrc()
            if netrc_info:
                netrc_login = netrc_info.authenticators(request.url.authority)
                if netrc_login:
                    username, _, password = netrc_login
                    assert password is not None
                    return BasicAuthMiddleware(username=username, password=password)

        return None

    @functools.lru_cache(1)
    def _get_netrc(self) -> typing.Optional[netrc.netrc]:
        return get_netrc()

    def _dispatcher_for_request(
        self, request: Request, proxies: typing.Dict[str, Dispatcher]
    ) -> Dispatcher:
        """Gets the Dispatcher instance that should be used for a given Request"""
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
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
    ) -> Request:
        """
        Build and return a request instance.
        """
        url = self.merge_url(url)
        headers = self.merge_headers(headers)
        cookies = self.merge_cookies(cookies)
        params = self.merge_queryparams(params)
        return Request(
            method,
            url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )

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
    ) -> Response:
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
    ) -> Response:
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
    ) -> Response:
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
        )

    async def post(
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
    ) -> Response:
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
        )

    async def put(
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
    ) -> Response:
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
        )

    async def patch(
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
    ) -> Response:
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
        )

    async def delete(
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
    ) -> Response:
        return await self.request(
            "DELETE",
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
        )

    async def request(
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
    ) -> Response:
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
        )
        return response

    async def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
        trust_env: bool = None,
    ) -> Response:
        return await self._get_response(
            request=request,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            verify=verify,
            cert=cert,
            timeout=timeout,
            trust_env=trust_env,
        )

    async def close(self) -> None:
        await self.dispatch.close()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()


def _proxies_to_dispatchers(
    proxies: typing.Optional[ProxiesTypes],
    verify: VerifyTypes,
    cert: typing.Optional[CertTypes],
    timeout: TimeoutTypes,
    http_versions: typing.Optional[HTTPVersionTypes],
    pool_limits: PoolLimits,
    backend: ConcurrencyBackend,
    trust_env: bool,
) -> typing.Dict[str, Dispatcher]:
    def _proxy_from_url(url: URLTypes) -> Dispatcher:
        nonlocal verify, cert, timeout, http_versions, pool_limits, backend, trust_env
        url = URL(url)
        if url.scheme in ("http", "https"):
            return HTTPProxy(
                url,
                verify=verify,
                cert=cert,
                timeout=timeout,
                pool_limits=pool_limits,
                backend=backend,
                trust_env=trust_env,
                http_versions=http_versions,
            )
        raise ValueError(f"Unknown proxy for {url!r}")

    if proxies is None:
        return {}
    elif isinstance(proxies, (str, URL)):
        return {"all": _proxy_from_url(proxies)}
    elif isinstance(proxies, Dispatcher):
        return {"all": proxies}
    else:
        new_proxies = {}
        for key, dispatcher_or_url in proxies.items():
            if isinstance(dispatcher_or_url, (str, URL)):
                new_proxies[str(key)] = _proxy_from_url(dispatcher_or_url)
            else:
                new_proxies[str(key)] = dispatcher_or_url
        return new_proxies
