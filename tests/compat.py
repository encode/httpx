import typing

try:
    from contextlib import nullcontext
except ImportError:  # pragma: no cover
    # Python < 3.7
    from contextlib import contextmanager

    @contextmanager  # type: ignore
    def nullcontext() -> typing.Iterator[None]:
        yield
