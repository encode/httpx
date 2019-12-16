"""
Utilities for managing optional dependencies.
"""

import functools
import typing


class RequiresHTTP2:
    def has_feature(self) -> bool:
        try:
            import h2  # noqa: F401
        except ImportError:  # pragma: no cover
            return False
        else:
            return True

    def __call__(self, func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        def wrapped(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            if not self.has_feature():
                raise RuntimeError(
                    "HTTP/2 dependencies are missing.\n"
                    "HINT: install them with 'pip install httpx[http2]'."
                )
            return func(*args, **kwargs)

        return wrapped


# Use a shared instance so that monkey-patching '.has_feature()' on this instance
# propagates the new behavior across the codebase.
requires_http2 = RequiresHTTP2()
