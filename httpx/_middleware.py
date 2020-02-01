import typing

from ._config import Timeout
from ._models import Request, Response
from ._utils import get_logger

logger = get_logger(__name__)


class MiddlewareInstance(typing.Protocol):
    def __call__(
        self, request: Request, timeout: Timeout, **kwargs: typing.Any
    ) -> typing.Generator[typing.Any, typing.Any, Response]:
        ...


MiddlewareType = typing.Callable[[MiddlewareInstance], MiddlewareInstance]


class Middleware:
    def __init__(self, middleware: typing.Callable, **kwargs: typing.Any) -> None:
        self.middleware = middleware
        self.kwargs = kwargs

    def __call__(self, get_response: MiddlewareInstance) -> MiddlewareInstance:
        return self.middleware(get_response, **self.kwargs)


class MiddlewareStack:
    """
    Container for representing a stack of middleware classes.
    """

    def __init__(
        self,
        get_response: MiddlewareInstance,
        middleware: typing.Sequence[Middleware] = None,
    ) -> None:
        self.get_response = get_response
        self.middleware = list(middleware) if middleware is not None else []

    def __call__(
        self, request: Request, timeout: Timeout, **kwargs: typing.Any
    ) -> typing.Generator[typing.Any, typing.Any, Response]:
        if not hasattr(self, "_stack"):
            get_response = self.get_response
            for middleware in self.middleware:
                get_response = middleware(get_response)
            self._stack = get_response

        return self._stack(request, timeout, **kwargs)
