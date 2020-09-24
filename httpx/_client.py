import datetime
import functools
import typing
import warnings
from types import TracebackType

import httpcore

from .__version__ import __version__
from ._auth import Auth, BasicAuth, FunctionAuth
from ._config import (
    DEFAULT_LIMITS,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_TIMEOUT_CONFIG,
    UNSET,
    Limits,
    Proxy,
    Timeout,
    UnsetType,
    create_ssl_context,
)
from ._decoders import SUPPORTED_DECODERS
from ._exceptions import (
    HTTPCORE_EXC_MAP,
    InvalidURL,
    RemoteProtocolError,
    TooManyRedirects,
    map_exceptions,
)
from ._models import URL, Cookies, Headers, QueryParams, Request, Response
from ._status_codes import codes
from ._transports.asgi import ASGITransport
from ._transports.wsgi import WSGITransport
from ._types import (
    AuthTypes,
    ByteStream,
    CertTypes,
    CookieTypes,
    HeaderTypes,
    ProxiesTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestFiles,
    TimeoutTypes,
    URLTypes,
    VerifyTypes,
)
from ._utils import (
    NetRCInfo,
    Timer,
    URLPattern,
    get_environment_proxies,
    get_logger,
    same_origin,
    warn_deprecated,
)

logger = get_logger(__name__)

KEEPALIVE_EXPIRY = 5.0
USER_AGENT = f"python-httpx/{__version__}"
ACCEPT_ENCODING = ", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != "identity"]
)


class BaseClient:
    def __init__(
        self,
        *,
        auth: AuthTypes = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = None,
        base_url: URLTypes = "",
        trust_env: bool = True,
    ):
        event_hooks = {} if event_hooks is None else event_hooks

        self._base_url = self._enforce_trailing_slash(URL(base_url))

        self._auth = self._build_auth(auth)
        self._params = QueryParams(params)
        self.headers = Headers(headers)
        self._cookies = Cookies(cookies)
        self._timeout = Timeout(timeout)
        self.max_redirects = max_redirects
        self._event_hooks = {
            "request": list(event_hooks.get("request", [])),
            "response": list(event_hooks.get("response", [])),
        }
        self._trust_env = trust_env
        self._netrc = NetRCInfo()
        self._is_closed = True

    @property
    def is_closed(self) -> bool:
        """
        Check if the client being closed
        """
        return self._is_closed

    @property
    def trust_env(self) -> bool:
        return self._trust_env

    def _enforce_trailing_slash(self, url: URL) -> URL:
        if url.path.endswith("/"):
            return url
        return url.copy_with(path=url.path + "/")

    def _get_proxy_map(
        self, proxies: typing.Optional[ProxiesTypes], allow_env_proxies: bool
    ) -> typing.Dict[str, typing.Optional[Proxy]]:
        if proxies is None:
            if allow_env_proxies:
                return {
                    key: None if url is None else Proxy(url=url)
                    for key, url in get_environment_proxies().items()
                }
            return {}
        if isinstance(proxies, dict):
            new_proxies = {}
            for key, value in proxies.items():
                proxy = Proxy(url=value) if isinstance(value, (str, URL)) else value
                new_proxies[str(key)] = proxy
            return new_proxies
        else:
            proxy = Proxy(url=proxies) if isinstance(proxies, (str, URL)) else proxies
            return {"all://": proxy}

    @property
    def timeout(self) -> Timeout:
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: TimeoutTypes) -> None:
        self._timeout = Timeout(timeout)

    @property
    def event_hooks(self) -> typing.Dict[str, typing.List[typing.Callable]]:
        return self._event_hooks

    @event_hooks.setter
    def event_hooks(
        self, event_hooks: typing.Dict[str, typing.List[typing.Callable]]
    ) -> None:
        self._event_hooks = {
            "request": list(event_hooks.get("request", [])),
            "response": list(event_hooks.get("response", [])),
        }

    @property
    def auth(self) -> typing.Optional[Auth]:
        """
        Authentication class used when none is passed at the request-level.

        See also [Authentication][0].

        [0]: /quickstart/#authentication
        """
        return self._auth

    @auth.setter
    def auth(self, auth: AuthTypes) -> None:
        self._auth = self._build_auth(auth)

    @property
    def base_url(self) -> URL:
        """
        Base URL to use when sending requests with relative URLs.
        """
        return self._base_url

    @base_url.setter
    def base_url(self, url: URLTypes) -> None:
        self._base_url = self._enforce_trailing_slash(URL(url))

    @property
    def headers(self) -> Headers:
        """
        HTTP headers to include when sending requests.
        """
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTypes) -> None:
        client_headers = Headers(
            {
                b"Accept": b"*/*",
                b"Accept-Encoding": ACCEPT_ENCODING.encode("ascii"),
                b"Connection": b"keep-alive",
                b"User-Agent": USER_AGENT.encode("ascii"),
            }
        )
        client_headers.update(headers)
        self._headers = client_headers

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

    def stream(
        self,
        method: str,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> "StreamContextManager":
        """
        Alternative to `httpx.request()` that streams the response body
        instead of loading it into memory at once.

        **Parameters**: See `httpx.request`.

        See also: [Streaming Responses][0]

        [0]: /quickstart#streaming-responses
        """
        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        return StreamContextManager(
            client=self,
            request=request,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def build_request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
    ) -> Request:
        """
        Build and return a request instance.

        * The `params`, `headers` and `cookies` arguments
        are merged with any values set on the client.
        * The `url` argument is merged with any `base_url` set on the client.

        See also: [Request instances][0]

        [0]: /advanced/#request-instances
        """
        url = self._merge_url(url)
        headers = self._merge_headers(headers)
        cookies = self._merge_cookies(cookies)
        params = self._merge_queryparams(params)
        return Request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )

    def _merge_url(self, url: URLTypes) -> URL:
        """
        Merge a URL argument together with any 'base_url' on the client,
        to create the URL used for the outgoing request.
        """
        merge_url = URL(url)
        if merge_url.is_relative_url:
            # We always ensure the base_url paths include the trailing '/',
            # and always strip any leading '/' from the merge URL.
            merge_url = merge_url.copy_with(path=merge_url.path.lstrip("/"))
            return self.base_url.join(merge_url)
        return merge_url

    def _merge_cookies(
        self, cookies: CookieTypes = None
    ) -> typing.Optional[CookieTypes]:
        """
        Merge a cookies argument together with any cookies on the client,
        to create the cookies used for the outgoing request.
        """
        if cookies or self.cookies:
            merged_cookies = Cookies(self.cookies)
            merged_cookies.update(cookies)
            return merged_cookies
        return cookies

    def _merge_headers(
        self, headers: HeaderTypes = None
    ) -> typing.Optional[HeaderTypes]:
        """
        Merge a headers argument together with any headers on the client,
        to create the headers used for the outgoing request.
        """
        merged_headers = Headers(self.headers)
        merged_headers.update(headers)
        return merged_headers

    def _merge_queryparams(
        self, params: QueryParamTypes = None
    ) -> typing.Optional[QueryParamTypes]:
        """
        Merge a queryparams argument together with any queryparams on the client,
        to create the queryparams used for the outgoing request.
        """
        if params or self.params:
            merged_queryparams = QueryParams(self.params)
            merged_queryparams.update(params)
            return merged_queryparams
        return params

    def _build_auth(self, auth: AuthTypes) -> typing.Optional[Auth]:
        if auth is None:
            return None
        elif isinstance(auth, tuple):
            return BasicAuth(username=auth[0], password=auth[1])
        elif isinstance(auth, Auth):
            return auth
        elif callable(auth):
            return FunctionAuth(func=auth)
        else:
            raise TypeError('Invalid "auth" argument.')

    def _build_request_auth(
        self, request: Request, auth: typing.Union[AuthTypes, UnsetType] = UNSET
    ) -> Auth:
        auth = self._auth if isinstance(auth, UnsetType) else self._build_auth(auth)

        if auth is not None:
            return auth

        username, password = request.url.username, request.url.password
        if username or password:
            return BasicAuth(username=username, password=password)

        if self.trust_env and "Authorization" not in request.headers:
            credentials = self._netrc.get_credentials(request.url.host)
            if credentials is not None:
                return BasicAuth(username=credentials[0], password=credentials[1])

        return Auth()

    def _build_redirect_request(self, request: Request, response: Response) -> Request:
        """
        Given a request and a redirect response, return a new request that
        should be used to effect the redirect.
        """
        method = self._redirect_method(request, response)
        url = self._redirect_url(request, response)
        headers = self._redirect_headers(request, url, method)
        stream = self._redirect_stream(request, method)
        cookies = Cookies(self.cookies)
        return Request(
            method=method, url=url, headers=headers, cookies=cookies, stream=stream
        )

    def _redirect_method(self, request: Request, response: Response) -> str:
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

    def _redirect_url(self, request: Request, response: Response) -> URL:
        """
        Return the URL for the redirect to follow.
        """
        location = response.headers["Location"]

        try:
            url = URL(location)
        except InvalidURL as exc:
            raise RemoteProtocolError(
                f"Invalid URL in location header: {exc}.", request=request
            ) from None

        # Handle malformed 'Location' headers that are "absolute" form, have no host.
        # See: https://github.com/encode/httpx/issues/771
        if url.scheme and not url.host:
            url = url.copy_with(host=request.url.host)

        # Facilitate relative 'Location' headers, as allowed by RFC 7231.
        # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
        if url.is_relative_url:
            url = request.url.join(url)

        # Attach previous fragment if needed (RFC 7231 7.1.2)
        if request.url.fragment and not url.fragment:
            url = url.copy_with(fragment=request.url.fragment)

        return url

    def _redirect_headers(self, request: Request, url: URL, method: str) -> Headers:
        """
        Return the headers that should be used for the redirect request.
        """
        headers = Headers(request.headers)

        if not same_origin(url, request.url):
            # Strip Authorization headers when responses are redirected away from
            # the origin.
            headers.pop("Authorization", None)

            # Remove the Host header, so that a new one will be auto-populated on
            # the request instance.
            headers.pop("Host", None)

        if method != request.method and method == "GET":
            # If we've switch to a 'GET' request, then strip any headers which
            # are only relevant to the request body.
            headers.pop("Content-Length", None)
            headers.pop("Transfer-Encoding", None)

        # We should use the client cookie store to determine any cookie header,
        # rather than whatever was on the original outgoing request.
        headers.pop("Cookie", None)

        return headers

    def _redirect_stream(
        self, request: Request, method: str
    ) -> typing.Optional[ByteStream]:
        """
        Return the body that should be used for the redirect request.
        """
        if method != request.method and method == "GET":
            return None

        return request.stream


class Client(BaseClient):
    """
    An HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc.

    Usage:

    ```python
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
    * **proxies** - *(optional)* A dictionary mapping proxy keys to proxy
    URLs.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    requests.
    * **limits** - *(optional)* The limits configuration to use.
    * **max_redirects** - *(optional)* The maximum number of redirect responses
    that should be followed.
    * **base_url** - *(optional)* A URL to use as the base when building
    request URLs.
    * **transport** - *(optional)* A transport class to use for sending requests
    over the network.
    * **app** - *(optional)* An WSGI application to send requests to,
    rather than sending actual network requests.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.
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
        http2: bool = False,
        proxies: ProxiesTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        limits: Limits = DEFAULT_LIMITS,
        pool_limits: Limits = None,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = None,
        base_url: URLTypes = "",
        transport: httpcore.SyncHTTPTransport = None,
        app: typing.Callable = None,
        trust_env: bool = True,
    ):
        super().__init__(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            trust_env=trust_env,
        )

        if http2:
            try:
                import h2  # noqa
            except ImportError:  # pragma: nocover
                raise ImportError(
                    "Using http2=True, but the 'h2' package is not installed. "
                    "Make sure to install httpx using `pip install httpx[http2]`."
                ) from None

        if pool_limits is not None:
            warn_deprecated(
                "Client(..., pool_limits=...) is deprecated and will raise "
                "errors in the future. Use Client(..., limits=...) instead."
            )
            limits = pool_limits

        allow_env_proxies = trust_env and app is None and transport is None
        proxy_map = self._get_proxy_map(proxies, allow_env_proxies)

        self._transport = self._init_transport(
            verify=verify,
            cert=cert,
            http2=http2,
            limits=limits,
            transport=transport,
            app=app,
            trust_env=trust_env,
        )
        self._proxies: typing.Dict[
            URLPattern, typing.Optional[httpcore.SyncHTTPTransport]
        ] = {
            URLPattern(key): None
            if proxy is None
            else self._init_proxy_transport(
                proxy,
                verify=verify,
                cert=cert,
                http2=http2,
                limits=limits,
                trust_env=trust_env,
            )
            for key, proxy in proxy_map.items()
        }
        self._proxies = dict(sorted(self._proxies.items()))

    def _init_transport(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        transport: httpcore.SyncHTTPTransport = None,
        app: typing.Callable = None,
        trust_env: bool = True,
    ) -> httpcore.SyncHTTPTransport:
        if transport is not None:
            return transport

        if app is not None:
            return WSGITransport(app=app)

        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        return httpcore.SyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=KEEPALIVE_EXPIRY,
            http2=http2,
        )

    def _init_proxy_transport(
        self,
        proxy: Proxy,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
    ) -> httpcore.SyncHTTPTransport:
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        return httpcore.SyncHTTPProxy(
            proxy_url=proxy.url.raw,
            proxy_headers=proxy.headers.raw,
            proxy_mode=proxy.mode,
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=KEEPALIVE_EXPIRY,
            http2=http2,
        )

    def _transport_for_url(self, url: URL) -> httpcore.SyncHTTPTransport:
        """
        Returns the transport instance that should be used for a given URL.
        This will either be the standard connection pool, or a proxy.
        """
        for pattern, transport in self._proxies.items():
            if pattern.matches(url):
                return self._transport if transport is None else transport

        return self._transport

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Build and send a request.

        Equivalent to:

        ```python
        request = client.build_request(...)
        response = client.send(request, ...)
        ```

        See `Client.build_request()`, `Client.send()` and
        [Merging of configuration][0] for how the various parameters
        are merged with client-level configuration.

        [0]: /advanced/#merging-of-configuration
        """
        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        return self.send(
            request, auth=auth, allow_redirects=allow_redirects, timeout=timeout
        )

    def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a request.

        The request is sent as-is, unmodified.

        Typically you'll want to build one with `Client.build_request()`
        so that any client-level configuration is merged into the request,
        but passing an explicit `httpx.Request()` is supported as well.

        See also: [Request instances][0]

        [0]: /advanced/#request-instances
        """
        self._is_closed = False

        timeout = self.timeout if isinstance(timeout, UnsetType) else Timeout(timeout)

        auth = self._build_request_auth(request, auth)

        response = self._send_handling_auth(
            request,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            history=[],
        )

        if not stream:
            try:
                response.read()
            finally:
                response.close()

        try:
            for hook in self._event_hooks["response"]:
                hook(response)
        except Exception:
            response.close()
            raise

        return response

    def _send_handling_auth(
        self,
        request: Request,
        auth: Auth,
        timeout: Timeout,
        allow_redirects: bool,
        history: typing.List[Response],
    ) -> Response:
        auth_flow = auth.sync_auth_flow(request)
        request = next(auth_flow)

        for hook in self._event_hooks["request"]:
            hook(request)

        while True:
            response = self._send_handling_redirects(
                request,
                timeout=timeout,
                allow_redirects=allow_redirects,
                history=history,
            )
            try:
                next_request = auth_flow.send(response)
            except StopIteration:
                return response
            except BaseException as exc:
                response.close()
                raise exc from None
            else:
                response.history = list(history)
                response.read()
                request = next_request
                history.append(response)

    def _send_handling_redirects(
        self,
        request: Request,
        timeout: Timeout,
        allow_redirects: bool,
        history: typing.List[Response],
    ) -> Response:
        while True:
            if len(history) > self.max_redirects:
                raise TooManyRedirects(
                    "Exceeded maximum allowed redirects.", request=request
                )

            response = self._send_single_request(request, timeout)
            response.history = list(history)

            if not response.is_redirect:
                return response

            if allow_redirects:
                response.read()
            request = self._build_redirect_request(request, response)
            history = history + [response]

            if not allow_redirects:
                response.call_next = functools.partial(
                    self._send_handling_redirects,
                    request=request,
                    timeout=timeout,
                    allow_redirects=False,
                    history=history,
                )
                return response

    def _send_single_request(self, request: Request, timeout: Timeout) -> Response:
        """
        Sends a single request, without handling any redirections.
        """
        transport = self._transport_for_url(request.url)
        timer = Timer()
        timer.sync_start()

        with map_exceptions(HTTPCORE_EXC_MAP, request=request):
            (status_code, headers, stream, ext) = transport.request(
                request.method.encode(),
                request.url.raw,
                headers=request.headers.raw,
                stream=request.stream,  # type: ignore
                ext={"timeout": timeout.as_dict()},
            )

        def on_close(response: Response) -> None:
            response.elapsed = datetime.timedelta(seconds=timer.sync_elapsed())
            if hasattr(stream, "close"):
                stream.close()

        response = Response(
            status_code,
            headers=headers,
            stream=stream,  # type: ignore
            ext=ext,
            request=request,
            on_close=on_close,
        )

        self.cookies.extract_cookies(response)

        status = f"{response.status_code} {response.reason_phrase}"
        response_line = f"{response.http_version} {status}"
        logger.debug(f'HTTP Request: {request.method} {request.url} "{response_line}"')

        return response

    def get(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def options(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send an `OPTIONS` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def head(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `HEAD` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def post(
        self,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `POST` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "POST",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def put(
        self,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `PUT` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "PUT",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def patch(
        self,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `PATCH` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "PATCH",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def delete(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `DELETE` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    def close(self) -> None:
        """
        Close transport and proxies.
        """
        if not self.is_closed:
            self._is_closed = True

            self._transport.close()
            for proxy in self._proxies.values():
                if proxy is not None:
                    proxy.close()

    def __enter__(self) -> "Client":
        self._transport.__enter__()
        for proxy in self._proxies.values():
            if proxy is not None:
                proxy.__enter__()
        self._is_closed = False
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        if not self.is_closed:
            self._is_closed = True

            self._transport.__exit__(exc_type, exc_value, traceback)
            for proxy in self._proxies.values():
                if proxy is not None:
                    proxy.__exit__(exc_type, exc_value, traceback)

    def __del__(self) -> None:
        self.close()


class AsyncClient(BaseClient):
    """
    An asynchronous HTTP client, with connection pooling, HTTP/2, redirects,
    cookie persistence, etc.

    Usage:

    ```python
    >>> async with httpx.AsyncClient() as client:
    >>>     response = await client.get('https://example.org')
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
    * **http2** - *(optional)* A boolean indicating if HTTP/2 support should be
    enabled. Defaults to `False`.
    * **proxies** - *(optional)* A dictionary mapping HTTP protocols to proxy
    URLs.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    requests.
    * **limits** - *(optional)* The limits configuration to use.
    * **max_redirects** - *(optional)* The maximum number of redirect responses
    that should be followed.
    * **base_url** - *(optional)* A URL to use as the base when building
    request URLs.
    * **transport** - *(optional)* A transport class to use for sending requests
    over the network.
    * **app** - *(optional)* An ASGI application to send requests to,
    rather than sending actual network requests.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.
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
        http2: bool = False,
        proxies: ProxiesTypes = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        limits: Limits = DEFAULT_LIMITS,
        pool_limits: Limits = None,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = None,
        base_url: URLTypes = "",
        transport: httpcore.AsyncHTTPTransport = None,
        app: typing.Callable = None,
        trust_env: bool = True,
    ):
        super().__init__(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            trust_env=trust_env,
        )

        if http2:
            try:
                import h2  # noqa
            except ImportError:  # pragma: nocover
                raise ImportError(
                    "Using http2=True, but the 'h2' package is not installed. "
                    "Make sure to install httpx using `pip install httpx[http2]`."
                ) from None

        if pool_limits is not None:
            warn_deprecated(
                "AsyncClient(..., pool_limits=...) is deprecated and will raise "
                "errors in the future. Use AsyncClient(..., limits=...) instead."
            )
            limits = pool_limits

        allow_env_proxies = trust_env and app is None and transport is None
        proxy_map = self._get_proxy_map(proxies, allow_env_proxies)

        self._transport = self._init_transport(
            verify=verify,
            cert=cert,
            http2=http2,
            limits=limits,
            transport=transport,
            app=app,
            trust_env=trust_env,
        )

        self._proxies: typing.Dict[
            URLPattern, typing.Optional[httpcore.AsyncHTTPTransport]
        ] = {
            URLPattern(key): None
            if proxy is None
            else self._init_proxy_transport(
                proxy,
                verify=verify,
                cert=cert,
                http2=http2,
                limits=limits,
                trust_env=trust_env,
            )
            for key, proxy in proxy_map.items()
        }
        self._proxies = dict(sorted(self._proxies.items()))

    def _init_transport(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        transport: httpcore.AsyncHTTPTransport = None,
        app: typing.Callable = None,
        trust_env: bool = True,
    ) -> httpcore.AsyncHTTPTransport:
        if transport is not None:
            return transport

        if app is not None:
            return ASGITransport(app=app)

        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        return httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=KEEPALIVE_EXPIRY,
            http2=http2,
        )

    def _init_proxy_transport(
        self,
        proxy: Proxy,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
    ) -> httpcore.AsyncHTTPTransport:
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        return httpcore.AsyncHTTPProxy(
            proxy_url=proxy.url.raw,
            proxy_headers=proxy.headers.raw,
            proxy_mode=proxy.mode,
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=KEEPALIVE_EXPIRY,
            http2=http2,
        )

    def _transport_for_url(self, url: URL) -> httpcore.AsyncHTTPTransport:
        """
        Returns the transport instance that should be used for a given URL.
        This will either be the standard connection pool, or a proxy.
        """
        for pattern, transport in self._proxies.items():
            if pattern.matches(url):
                return self._transport if transport is None else transport

        return self._transport

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Build and send a request.

        Equivalent to:

        ```python
        request = client.build_request(...)
        response = await client.send(request, ...)
        ```

        See `AsyncClient.build_request()`, `AsyncClient.send()`
        and [Merging of configuration][0] for how the various parameters
        are merged with client-level configuration.

        [0]: /advanced/#merging-of-configuration
        """
        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        response = await self.send(
            request, auth=auth, allow_redirects=allow_redirects, timeout=timeout
        )
        return response

    async def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a request.

        The request is sent as-is, unmodified.

        Typically you'll want to build one with `AsyncClient.build_request()`
        so that any client-level configuration is merged into the request,
        but passing an explicit `httpx.Request()` is supported as well.

        See also: [Request instances][0]

        [0]: /advanced/#request-instances
        """
        self._is_closed = False

        timeout = self.timeout if isinstance(timeout, UnsetType) else Timeout(timeout)

        auth = self._build_request_auth(request, auth)

        response = await self._send_handling_auth(
            request,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            history=[],
        )

        if not stream:
            try:
                await response.aread()
            finally:
                await response.aclose()

        try:
            for hook in self._event_hooks["response"]:
                await hook(response)
        except Exception:
            await response.aclose()
            raise

        return response

    async def _send_handling_auth(
        self,
        request: Request,
        auth: Auth,
        timeout: Timeout,
        allow_redirects: bool,
        history: typing.List[Response],
    ) -> Response:
        auth_flow = auth.async_auth_flow(request)
        request = await auth_flow.__anext__()

        for hook in self._event_hooks["request"]:
            await hook(request)

        while True:
            response = await self._send_handling_redirects(
                request,
                timeout=timeout,
                allow_redirects=allow_redirects,
                history=history,
            )
            try:
                next_request = await auth_flow.asend(response)
            except StopAsyncIteration:
                return response
            except BaseException as exc:
                await response.aclose()
                raise exc from None
            else:
                response.history = list(history)
                await response.aread()
                request = next_request
                history.append(response)

    async def _send_handling_redirects(
        self,
        request: Request,
        timeout: Timeout,
        allow_redirects: bool,
        history: typing.List[Response],
    ) -> Response:
        while True:
            if len(history) > self.max_redirects:
                raise TooManyRedirects(
                    "Exceeded maximum allowed redirects.", request=request
                )

            response = await self._send_single_request(request, timeout)
            response.history = list(history)

            if not response.is_redirect:
                return response

            if allow_redirects:
                await response.aread()
            request = self._build_redirect_request(request, response)
            history = history + [response]

            if not allow_redirects:
                response.call_next = functools.partial(
                    self._send_handling_redirects,
                    request=request,
                    timeout=timeout,
                    allow_redirects=False,
                    history=history,
                )
                return response

    async def _send_single_request(
        self, request: Request, timeout: Timeout
    ) -> Response:
        """
        Sends a single request, without handling any redirections.
        """
        transport = self._transport_for_url(request.url)
        timer = Timer()
        await timer.async_start()

        with map_exceptions(HTTPCORE_EXC_MAP, request=request):
            (status_code, headers, stream, ext,) = await transport.arequest(
                request.method.encode(),
                request.url.raw,
                headers=request.headers.raw,
                stream=request.stream,  # type: ignore
                ext={"timeout": timeout.as_dict()},
            )

        async def on_close(response: Response) -> None:
            response.elapsed = datetime.timedelta(seconds=await timer.async_elapsed())
            if hasattr(stream, "aclose"):
                await stream.aclose()

        response = Response(
            status_code,
            headers=headers,
            stream=stream,  # type: ignore
            ext=ext,
            request=request,
            on_close=on_close,
        )

        self.cookies.extract_cookies(response)

        status = f"{response.status_code} {response.reason_phrase}"
        response_line = f"{response.http_version} {status}"
        logger.debug(f'HTTP Request: {request.method} {request.url} "{response_line}"')

        return response

    async def get(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def options(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send an `OPTIONS` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def head(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `HEAD` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def post(
        self,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `POST` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "POST",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def put(
        self,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `PUT` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "PUT",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def patch(
        self,
        url: URLTypes,
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `PATCH` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "PATCH",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def delete(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
    ) -> Response:
        """
        Send a `DELETE` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        """
        Close transport and proxies.
        """
        if not self.is_closed:
            self._is_closed = True

            await self._transport.aclose()
            for proxy in self._proxies.values():
                if proxy is not None:
                    await proxy.aclose()

    async def __aenter__(self) -> "AsyncClient":
        await self._transport.__aenter__()
        for proxy in self._proxies.values():
            if proxy is not None:
                await proxy.__aenter__()
        self._is_closed = False
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        if not self.is_closed:
            self._is_closed = True
            await self._transport.__aexit__(exc_type, exc_value, traceback)
            for proxy in self._proxies.values():
                if proxy is not None:
                    await proxy.__aexit__(exc_type, exc_value, traceback)

    def __del__(self) -> None:
        if not self.is_closed:
            warnings.warn(
                f"Unclosed {self!r}. "
                "See https://www.python-httpx.org/async/#opening-and-closing-clients "
                "for details."
            )


class StreamContextManager:
    def __init__(
        self,
        client: BaseClient,
        request: Request,
        *,
        auth: typing.Union[AuthTypes, UnsetType] = UNSET,
        allow_redirects: bool = True,
        timeout: typing.Union[TimeoutTypes, UnsetType] = UNSET,
        close_client: bool = False,
    ) -> None:
        self.client = client
        self.request = request
        self.auth = auth
        self.allow_redirects = allow_redirects
        self.timeout = timeout
        self.close_client = close_client

    def __enter__(self) -> "Response":
        assert isinstance(self.client, Client)
        self.response = self.client.send(
            request=self.request,
            auth=self.auth,
            allow_redirects=self.allow_redirects,
            timeout=self.timeout,
            stream=True,
        )
        return self.response

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        assert isinstance(self.client, Client)
        self.response.close()
        if self.close_client:
            self.client.close()

    async def __aenter__(self) -> "Response":
        assert isinstance(self.client, AsyncClient)
        self.response = await self.client.send(
            request=self.request,
            auth=self.auth,
            allow_redirects=self.allow_redirects,
            timeout=self.timeout,
            stream=True,
        )
        return self.response

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        assert isinstance(self.client, AsyncClient)
        await self.response.aclose()
