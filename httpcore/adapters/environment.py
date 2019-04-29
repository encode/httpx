import typing

from ..interfaces import Adapter
from ..models import Request, Response


class EnvironmentAdapter(Adapter):
    def __init__(self, dispatch: Adapter, trust_env: bool = True):
        self.dispatch = dispatch
        self.trust_env = trust_env

    def prepare_request(self, request: Request) -> None:
        self.dispatch.prepare_request(request)

    async def send(self, request: Request, **options: typing.Any) -> Response:
        if self.trust_env:
            self.merge_environment_options(options)
        return await self.dispatch.send(request, **options)

    async def close(self) -> None:
        await self.dispatch.close()

    def merge_environment_options(self, options: dict) -> None:
        """
        Add environment options.
        """
        #  TODO
