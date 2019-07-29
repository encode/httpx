import typing

from ..models import AsyncRequest, AsyncResponse


class BaseMiddleware:
    def process_request(self, request: AsyncRequest) -> AsyncRequest:
        return request

    def process_response(
        self, request: AsyncRequest, response: AsyncResponse
    ) -> typing.Union[AsyncRequest, AsyncResponse]:
        return response
