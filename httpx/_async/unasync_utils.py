import typing


def is_async_mode() -> bool:  # pragma: no cover
    """
    Return True if we are in the '_async' part of the code,
    or False if we are in the '_sync' part of the code.
    """

    async def f() -> int:
        return 0

    coro = f()
    if coro == 0:  # `unasync` stripped 'async' from the definition of 'f()'.
        return False

    coroutine = typing.cast(typing.Coroutine, coro)
    coroutine.close()  # Prevent unawaited coroutine warning.
    return True
