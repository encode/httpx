try:
    # Python 3.6 backport w/ asyncio support.
    # Try to import it first since it installs the contextvars backport too.
    import aiocontextvars as _contextvars
except ImportError:
    import contextvars as _contextvars  # type: ignore

ContextVar = _contextvars.ContextVar
