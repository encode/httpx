import typing
from urllib.parse import urljoin, urlparse

from ..config import DEFAULT_MAX_REDIRECTS
from ..exceptions import RedirectBodyUnavailable, RedirectLoop, TooManyRedirects
from ..interfaces import Adapter
from ..models import URL, Headers, Request, Response
from ..status_codes import codes
from ..utils import requote_uri


class RedirectAdapter(Adapter):
    def __init__(self, dispatch: Adapter, max_redirects: int = DEFAULT_MAX_REDIRECTS):
        self.dispatch = dispatch
        self.max_redirects = max_redirects

    def prepare_request(self, request: Request) -> None:
        self.dispatch.prepare_request(request)

    async def send(self, request: Request, **options: typing.Any) -> Response:
        allow_redirects = options.pop("allow_redirects", True)
        history = []  # type: typing.List[Response]
        seen_urls = set((request.url,))

        while True:
            response = await self.dispatch.send(request, **options)
            response.history = list(history)
            if not allow_redirects or not response.is_redirect:
                break
            history.append(response)
            if len(history) > self.max_redirects:
                raise TooManyRedirects()
            request = self.build_redirect_request(request, response)
            if request.url in seen_urls:
                raise RedirectLoop()
            seen_urls.add(request.url)

        return response

    async def close(self) -> None:
        await self.dispatch.close()

    def build_redirect_request(self, request: Request, response: Response) -> Request:
        method = self.redirect_method(request, response)
        url = self.redirect_url(request, response)
        headers = self.redirect_headers(request, url)
        body = self.redirect_body(request, method)
        return Request(method=method, url=url, headers=headers, body=body)

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
        location = response.headers["Location"]

        # Handle redirection without scheme (see: RFC 1808 Section 4)
        if location.startswith("//"):
            location = f"{request.url.scheme}:{location}"

        # Normalize url case and attach previous fragment if needed (RFC 7231 7.1.2)
        parsed = urlparse(location)
        if parsed.fragment == "" and request.url.fragment:
            parsed = parsed._replace(fragment=request.url.fragment)
        url = parsed.geturl()

        # Facilitate relative 'location' headers, as allowed by RFC 7231.
        # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
        # Compliant with RFC3986, we percent encode the url.
        if not parsed.netloc:
            url = urljoin(str(request.url), requote_uri(url))
        else:
            url = requote_uri(url)

        return URL(url)

    def redirect_headers(self, request: Request, url: URL) -> Headers:
        headers = Headers(request.headers)
        if url.origin != request.url.origin:
            del headers["Authorization"]
        return headers

    def redirect_body(self, request: Request, method: str) -> bytes:
        if method != request.method and method == "GET":
            return b""
        if request.is_streaming:
            raise RedirectBodyUnavailable()
        return request.body
