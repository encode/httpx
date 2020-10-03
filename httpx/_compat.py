try:
    from contextlib import AsyncExitStack  # type: ignore  # Py3.6
except ImportError:  # pragma: no cover
    # Python 3.6
    from async_exit_stack import AsyncExitStack  # type: ignore  # noqa: F401
