import functools
import typing

from ..config import DEFAULT_MAX_REDIRECTS
from ..exceptions import RedirectBodyUnavailable, RedirectLoop, TooManyRedirects
from ..models import URL, AsyncRequest, AsyncResponse, Cookies, Headers
from ..status_codes import codes
from .base import BaseMiddleware


class RedirectMiddleware(BaseMiddleware):
    def __init__(
        self,
        allow_redirects: bool = True,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        cookies: typing.Optional[Cookies] = None,
    ):
        self.allow_redirects = allow_redirects
        self.max_redirects = max_redirects
        self.cookies = cookies
        self.history: typing.List[AsyncResponse] = []

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        if len(self.history) > self.max_redirects:
            raise TooManyRedirects()
        if request.url in (response.url for response in self.history):
            raise RedirectLoop()

        response = await get_response(request)
        response.history = list(self.history)

        if not response.is_redirect:
            return response

        self.history.append(response)
        next_request = self.build_redirect_request(request, response)

        if self.allow_redirects:
            return await self(next_request, get_response)

        response.call_next = functools.partial(self, next_request, get_response)
        return response

    def build_redirect_request(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> AsyncRequest:
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url, method)  # TODO: merge headers?
        content = self.redirect_content(request, method)
        cookies = Cookies(self.cookies)
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

    def redirect_headers(self, request: AsyncRequest, url: URL, method: str) -> Headers:
        """
        Return the headers that should be used for the redirect request.
        """
        headers = Headers(request.headers)

        if url.origin != request.url.origin:
            # Strip Authorization headers when responses are redirected away from
            # the origin.
            headers.pop("Authorization", None)
            headers["Host"] = url.authority

        if method != request.method and method == "GET":
            # If we've switch to a 'GET' request, then strip any headers which
            # are only relevant to the request body.
            headers.pop("Content-Length", None)
            headers.pop("Transfer-Encoding", None)
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
