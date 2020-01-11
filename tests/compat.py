try:
    from contextlib import nullcontext
except ImportError:  # pragma: no cover
    # Python 3.6
    from contextlib import contextmanager

    @contextmanager
    def nullcontext():  # type: ignore
        yield None
