import typing

import sniffio

if typing.TYPE_CHECKING:  # pragma: no cover
    try:
        from typing import Protocol
    except ImportError:
        from typing_extensions import Protocol  # type: ignore

    class Event(Protocol):
        def set(self) -> None:
            ...

        # asyncio wait() returns True, but Trio returns None: ignore the return value.
        async def wait(self) -> typing.Any:
            ...

        def is_set(self) -> bool:
            ...


def create_event() -> "Event":
    if sniffio.current_async_library() == "trio":
        import trio

        return trio.Event()
    else:
        import asyncio

        return asyncio.Event()
