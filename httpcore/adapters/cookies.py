import typing

from ..interfaces import Adapter
from ..models import Request, Response


class CookieAdapter(Adapter):
    def __init__(self, dispatch: Adapter):
        self.dispatch = dispatch

    def prepare_request(self, request: Request) -> None:
        self.dispatch.prepare_request(request)

    async def send(self, request: Request, **options: typing.Any) -> Response:
        return await self.dispatch.send(request, **options)

    async def close(self) -> None:
        await self.dispatch.close()
