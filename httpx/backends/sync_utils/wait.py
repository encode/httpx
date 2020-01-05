"""
Adapted from:
https://github.com/python-trio/urllib3/blob/f5ff1acf157c167e549c941ee19715341cba2b58/src/urllib3/util/wait.py
"""

import select
import socket
import typing


class NoWayToWaitForSocketError(Exception):
    pass


def select_wait_for_socket(
    sock: socket.socket, read: bool = False, write: bool = False, timeout: float = None
) -> bool:
    if not read and not write:
        raise RuntimeError("must specify at least one of read=True, write=True")
    rcheck = []
    wcheck = []
    if read:
        rcheck.append(sock)
    if write:
        wcheck.append(sock)
    # When doing a non-blocking connect, most systems signal success by
    # marking the socket writable. Windows, though, signals success by marked
    # it as "exceptional". We paper over the difference by checking the write
    # sockets for both conditions. (The stdlib selectors module does the same
    # thing.)
    rready, wready, xready = select.select(rcheck, wcheck, wcheck, timeout)
    return bool(rready or wready or xready)


def poll_wait_for_socket(
    sock: socket.socket, read: bool = False, write: bool = False, timeout: float = None
) -> bool:
    if not read and not write:
        raise RuntimeError("must specify at least one of read=True, write=True")
    mask = 0
    if read:
        mask |= select.POLLIN
    if write:
        mask |= select.POLLOUT
    poll_obj = select.poll()
    poll_obj.register(sock, mask)

    # For some reason, poll() takes timeout in milliseconds
    def do_poll(t: typing.Optional[float]) -> typing.Any:
        if t is not None:
            t *= 1000
        return poll_obj.poll(t)

    return bool(do_poll(timeout))


def null_wait_for_socket(
    sock: socket.socket, read: bool = False, write: bool = False, timeout: float = None
) -> typing.NoReturn:
    raise NoWayToWaitForSocketError("no select-equivalent available")


def _have_working_poll() -> bool:
    # Apparently some systems have a select.poll that fails as soon as you try
    # to use it, either due to strange configuration or broken monkeypatching
    # from libraries like eventlet/greenlet.
    try:
        poll_obj = select.poll()
        poll_obj.poll(0)
    except (AttributeError, OSError):
        return False
    else:
        return True


def wait_for_socket(
    sock: socket.socket, read: bool = False, write: bool = False, timeout: float = None
) -> bool:
    # We delay choosing which implementation to use until the first time we're
    # called. We could do it at import time, but then we might make the wrong
    # decision if someone goes wild with monkeypatching select.poll after
    # we're imported.
    global wait_for_socket
    if _have_working_poll():
        wait_for_socket = poll_wait_for_socket
    elif hasattr(select, "select"):
        wait_for_socket = select_wait_for_socket
    else:  # Platform-specific: Appengine.
        wait_for_socket = null_wait_for_socket
    return wait_for_socket(sock, read=read, write=write, timeout=timeout)
