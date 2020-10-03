try:
    from contextlib import AsyncExitStack, asynccontextmanager  # type: ignore  # Py3.6
except ImportError:  # pragma: no cover
    # Python 3.6
    from async_exit_stack import AsyncExitStack  # type: ignore  # noqa: F401
    from async_generator import asynccontextmanager  # type: ignore  # noqa: F401

# These will be imported by the unasynced code.
from contextlib import ExitStack, contextmanager  # noqa: F401
