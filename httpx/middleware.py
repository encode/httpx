import functools
import typing

from .auth import Auth, AuthTypes, BasicAuth, FunctionAuth
from .config import Timeout
from .content_streams import ContentStream
from .dispatch.base import AsyncDispatcher, SyncDispatcher
from .exceptions import (
    HTTPError,
    RedirectLoop,
    RequestBodyUnavailable,
    TooManyRedirects,
)
from .models import URL, Cookies, Headers, Origin, Request, Response
from .status_codes import codes
from .utils import NetRCInfo, SyncOrAsync, get_logger

logger = get_logger(__name__)

Context = typing.Dict[str, typing.Any]
Middleware = typing.Callable[
    [Request, Context, Timeout], typing.Generator[typing.Any, typing.Any, Response]
]


class MiddlewareStack:
    """
    Container for representing a stack of middleware classes.
    """

    def __init__(self) -> None:
        StackItem = typing.Tuple[typing.Callable[..., Middleware], dict]
        self.stack: typing.List[StackItem] = []

    def add(self, cls: typing.Callable[..., Middleware], **kwargs: typing.Any) -> None:
        self.stack.append((cls, kwargs))

    def _build(self) -> Middleware:
        middleware: Middleware = SendSingleRequest()
        for cls, kwargs in self.stack:
            middleware = cls(middleware, **kwargs)
        return middleware

    def __call__(
        self, request: Request, context: Context, timeout: Timeout
    ) -> typing.Generator[typing.Any, typing.Any, Response]:
        if not hasattr(self, "_middleware"):
            self._middleware = self._build()
        return self._middleware(request, context, timeout)


class SendSingleRequest:
    """
    Sends a single request, without handling any redirections.
    """

    def __call__(
        self, request: Request, context: Context, timeout: Timeout
    ) -> typing.Generator[typing.Any, typing.Any, Response]:
        dispatcher: typing.Union[SyncDispatcher, AsyncDispatcher] = (
            context["dispatcher"]
        )
        cookies: Cookies = context["cookies"]

        try:
            response = yield dispatcher.send(request, timeout=timeout)
        except HTTPError as exc:
            # Add the original request to any HTTPError unless
            # there'a already a request attached in the case of
            # a ProxyError.
            if exc.request is None:
                exc.request = request
            raise

        cookies.extract_cookies(response)

        status = f"{response.status_code} {response.reason_phrase}"
        response_line = f"{response.http_version} {status}"
        logger.debug(f'HTTP Request: {request.method} {request.url} "{response_line}"')

        return response


class RedirectMiddleware:
    """
    Handle redirect responses.
    """

    def __init__(self, parent: Middleware, *, max_redirects: int) -> None:
        self.parent = parent
        self.max_redirects = max_redirects

    def __call__(
        self, request: Request, context: Context, timeout: Timeout,
    ) -> typing.Generator[typing.Any, typing.Any, Response]:
        allow_redirects: bool = context["allow_redirects"]
        context.setdefault("history", [])

        while True:
            history: typing.List[Response] = context["history"]

            if len(history) > self.max_redirects:
                raise TooManyRedirects()
            urls = ((resp.request.method, resp.url) for resp in history)
            if (request.method, request.url) in urls:
                raise RedirectLoop()

            response = yield from self.parent(request, context, timeout)
            response.history = list(history)

            if not response.is_redirect:
                return response

            if allow_redirects:
                yield SyncOrAsync(response.read, response.aread)

            request = self.build_redirect_request(request, response, context)
            context["history"] = history + [response]

            if not allow_redirects:
                response.call_next = functools.partial(self, request, context, timeout)
                return response

    def build_redirect_request(
        self, request: Request, response: Response, context: Context
    ) -> Request:
        """
        Given a request and a redirect response, return a new request that
        should be used to effect the redirect.
        """
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url, method)
        stream = self.redirect_stream(request, method)
        cookies = Cookies(context["cookies"])
        return Request(
            method=method, url=url, headers=headers, cookies=cookies, stream=stream
        )

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

    def redirect_headers(self, request: Request, url: URL, method: str) -> Headers:
        """
        Return the headers that should be used for the redirect request.
        """
        headers = Headers(request.headers)

        if Origin(url) != Origin(request.url):
            # Strip Authorization headers when responses are redirected away from
            # the origin.
            headers.pop("Authorization", None)
            headers["Host"] = url.authority

        if method != request.method and method == "GET":
            # If we've switch to a 'GET' request, then strip any headers which
            # are only relevant to the request body.
            headers.pop("Content-Length", None)
            headers.pop("Transfer-Encoding", None)

        # We should use the client cookie store to determine any cookie header,
        # rather than whatever was on the original outgoing request.
        headers.pop("Cookie", None)

        return headers

    def redirect_stream(
        self, request: Request, method: str
    ) -> typing.Optional[ContentStream]:
        """
        Return the body that should be used for the redirect request.
        """
        if method != request.method and method == "GET":
            return None

        if not request.stream.can_replay():
            raise RequestBodyUnavailable(
                "Got a redirect response, but the request body was streaming "
                "and is no longer available."
            )

        return request.stream


class AuthMiddleware:
    """
    Handle authentication.
    """

    def __init__(self, parent: Middleware):
        self.parent = parent
        self.netrc = NetRCInfo()

    def _build_auth(
        self, request: Request, trust_env: bool, auth: AuthTypes = None
    ) -> Auth:
        if auth is not None:
            if isinstance(auth, tuple):
                return BasicAuth(username=auth[0], password=auth[1])
            elif isinstance(auth, Auth):
                return auth
            elif callable(auth):
                return FunctionAuth(func=auth)
            raise TypeError('Invalid "auth" argument.')

        username, password = request.url.username, request.url.password
        if username or password:
            return BasicAuth(username=username, password=password)

        if trust_env and "Authorization" not in request.headers:
            credentials = self.netrc.get_credentials(request.url.authority)
            if credentials is not None:
                return BasicAuth(username=credentials[0], password=credentials[1])

        return Auth()

    def __call__(
        self, request: Request, context: Context, timeout: Timeout,
    ) -> typing.Generator[typing.Any, typing.Any, Response]:
        auth = self._build_auth(
            request, trust_env=context["trust_env"], auth=context["auth"]
        )
        history: typing.List[Response] = context.get("history", [])

        if auth.requires_request_body:
            yield SyncOrAsync(request.read, request.aread)

        auth_flow = auth.auth_flow(request)
        request = next(auth_flow)
        while True:
            response: Response = (yield from self.parent(request, context, timeout))
            try:
                next_request = auth_flow.send(response)
            except StopIteration:
                return response
            except BaseException as exc:
                yield SyncOrAsync(response.close, response.aclose)
                raise exc from None
            else:
                response.history = list(history)
                yield response.aread()
                request = next_request
                history.append(response)
