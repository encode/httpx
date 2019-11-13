import sys

if sys.version_info < (3, 7):
    try:
        from async_exit_stack import AsyncExitStack  # type: ignore
    except ImportError:
        raise RuntimeError(
            "AsyncExitStack is not available on Python 3.6, and no backport is "
            "installed. To install it, run: 'pip install async-exit-stack'."
        )
else:
    from contextlib import AsyncExitStack

__all__ = ["AsyncExitStack"]
