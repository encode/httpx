# `contextlib.asynccontextmanager` exists from Python 3.7 onwards.
# For 3.6 we require the `async_generator` package for a backported version.
try:
    from contextlib import asynccontextmanager  # type: ignore
except ImportError:  # pragma: no cover
    from async_generator import asynccontextmanager  # type: ignore # noqa

# Brotli support is optional
# The C bindings in `brotli` are recommended for CPython.
# The CFFI bindings in `brotlicffi` are recommended for PyPy and everything else.
try:
    import brotlicffi as brotli
except ImportError:  # pragma: nocover
    try:
        import brotli
    except ImportError:
        brotli = None
