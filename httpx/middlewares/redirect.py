import typing

from ..models import AsyncRequest, AsyncResponse, AuthTypes, URL, Headers, Cookies
from ..config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_TIMEOUT_CONFIG,
    CertTypes,
    PoolLimits,
    TimeoutTypes,
    VerifyTypes,
)
from ..exceptions import RedirectLoop, RedirectBodyUnavailable, TooManyRedirects
from ..status_codes import codes
from .base import BaseMiddleware


class RedirectMiddleware(BaseMiddleware):
    def __init__(
        self,
        allow_redirects,
        *,
        base_cookies: typing.Optional[Cookies] = None,
        max_redirects: typing.Optional[int] = None,
    ):
        self.allow_redirects = allow_redirects
        self.base_cookies = Cookies(base_cookies)
        self.max_redirects = max_redirects or DEFAULT_MAX_REDIRECTS
        self.history = []  # type: list

    def process_request(self, request: AsyncRequest) -> AsyncRequest:
        # We perform these checks here, so that calls to `response.next()`
        # will raise redirect errors if appropriate.
        if len(self.history) > self.max_redirects:
            raise TooManyRedirects()
        if request.url in [response.url for response in self.history]:
            raise RedirectLoop()

        return request

    def process_response(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> typing.Union[AsyncRequest, AsyncResponse]:
        if not response.is_redirect:
            response.history = list(self.history)
            return response

        self.history.append(response)
        next_request = self.build_redirect_request(request, response)
        if not self.allow_redirects:
            # FIXME: this breaks the request.next functionality
            # maybe we could make it a descriptor that performs the request?
            response.next = next_request
            return response
        else:
            return next_request

    def build_redirect_request(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> AsyncRequest:
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url)  # TODO: merge headers?
        content = self.redirect_content(request, method)
        cookies = Cookies(self.base_cookies)
        cookies.update(request.cookies)
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
