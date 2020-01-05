import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from .dispatch.base import AsyncDispatcher  # noqa: F401
    from ..models import URLTypes  # noqa: F401

AsyncProxiesTypes = typing.Union[
    "URLTypes",
    "AsyncDispatcher",
    typing.Dict["URLTypes", typing.Union["URLTypes", "AsyncDispatcher"]],
]
