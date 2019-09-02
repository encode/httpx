import functools
import inspect
import typing


def share_signature(source: typing.Callable) -> typing.Callable:
    sig = inspect.signature(source)

    def wrap(func):  # type: ignore
        @functools.wraps(func)
        def wrapped(*args, **kwargs):  # type: ignore
            return func(*args, **kwargs)

        wrapped.__signature__ = sig
        return wrapped

    return wrap
