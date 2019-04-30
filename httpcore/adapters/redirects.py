import typing

from ..config import DEFAULT_MAX_REDIRECTS
from ..exceptions import RedirectBodyUnavailable, RedirectLoop, TooManyRedirects
from ..interfaces import Adapter
from ..models import URL, Headers, Request, Response
from ..status_codes import codes


class RedirectAdapter(Adapter):
    def __init__(self, dispatch: Adapter, max_redirects: int = DEFAULT_MAX_REDIRECTS):
        self.dispatch = dispatch
        self.max_redirects = max_redirects

    def prepare_request(self, request: Request) -> None:
        self.dispatch.prepare_request(request)

    async def send(self, request: Request, **options: typing.Any) -> Response:
        allow_redirects = options.pop("allow_redirects", True)  # type: bool

        # The following will not typically be specified by the end-user developer,
        # but are included in `response.next()` calls.
        history = options.pop("history", [])  # type: typing.List[Response]
        seen_urls = options.pop("seen_urls", set())  # type: typing.Set[URL]

        while True:
            # We perform these checks here, so that calls to `response.next()`
            # will raise redirect errors if appropriate.
            if len(history) > self.max_redirects:
                raise TooManyRedirects()
            if request.url in seen_urls:
                raise RedirectLoop()

            response = await self.dispatch.send(request, **options)
            response.history = list(history)
            if not response.is_redirect:
                break

            history.insert(0, response)
            seen_urls.add(request.url)

            if allow_redirects:
                request = self.build_redirect_request(request, response)
            else:
                next_options = dict(options)
                next_options["seen_urls"] = seen_urls
                next_options["history"] = history

                async def send_next() -> Response:
                    nonlocal request, response, next_options
                    request = self.build_redirect_request(request, response)
                    response = await self.send(request, **next_options)
                    return response

                response.next = send_next  # type: ignore
                break

        return response

    async def close(self) -> None:
        await self.dispatch.close()

    def build_redirect_request(self, request: Request, response: Response) -> Request:
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url)
        content = self.redirect_content(request, method)
        return Request(method=method, url=url, headers=headers, content=content)

    def redirect_method(self, request: Request, response: Response) -> str:
        """
        When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.see_other and method != "HEAD":
            method = "GET"

        # Do what the browsers do, despite standards...
        # Turn 302s into GETs.
        if response.status_code == codes.found and method != "HEAD":
            method = "GET"

        # If a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in 'requests' issue 1704.
        if response.status_code == codes.moved_permanently and method == "POST":
            method = "GET"

        return method

    def redirect_url(self, request: Request, response: Response) -> URL:
        """
        Return the URL for the redirect to follow.
        """
        location = response.headers["Location"]

        url = URL(location, allow_relative=True)

        # Facilitate relative 'location' headers, as allowed by RFC 7231.
        # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
        # Compliant with RFC3986, we percent encode the url.
        if not url.is_absolute:
            url = url.resolve_with(request.url.copy_with(fragment=None))

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
