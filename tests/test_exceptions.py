import pytest

import httpx


def test_httpx_exceptions_exposed() -> None:
    """
    All exception classes defined in `httpx._exceptions`
    are exposed as public API.
    """

    not_exposed = [
        value
        for name, value in vars(httpx._exceptions).items()
        if isinstance(value, type)
        and issubclass(value, Exception)
        and not hasattr(httpx, name)
    ]

    if not_exposed:
        pytest.fail(f"Unexposed HTTPX exceptions: {not_exposed}")
