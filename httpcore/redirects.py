import typing

from .adapters import Adapter
from .exceptions import TooManyRedirects
from .models import Request, Response


class RedirectAdapter(Adapter):
    def __init__(self, dispatch: Adapter, max_redirects: int):
        self.dispatch = dispatch
        self.max_redirects = max_redirects

    def prepare_request(self, request: Request) -> None:
        self.dispatch.prepare_request(request)

    async def send(self, request: Request, **options: typing.Any) -> Response:
        allow_redirects = options.pop("allow_redirects", True)
        history = []

        while True:
            response = await self.dispatch.send(request, **options)
            if not allow_redirects or not response.is_redirect:
                break
            history.append(response)
            if len(history) > self.max_redirects:
                raise TooManyRedirects()
            request = self.build_redirect_request(request, response)

        return response

    async def close(self) -> None:
        self.dispatch.close()

    def build_redirect_request(self, request: Request, response: Response) -> Request:
        raise NotImplementedError()
