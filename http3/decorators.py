import functools
import typing

from .exceptions import NotConnected


def safe_connection_error(function: typing.Callable) -> typing.Callable:
    """
    Handle ConnectionResetError to keep the connection alive
    """

    @functools.wraps(function)
    async def wrapper(*args, **kwargs):  # type: ignore
        try:
            return await function(*args, **kwargs)
        except ConnectionResetError:  # pragma: nocover
            # We're currently testing this case in HTTP/2.
            # Really we should test it here too, but this'll do in the meantime.
            raise NotConnected() from None

    return wrapper
