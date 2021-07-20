"""
Some of our tests require branching of flow control.

We'd like to have the same kind of test for both async and sync environments,
and so we have functionality here that replicate's Trio's `open_nursery` API,
but in a plain old multi-threaded context.

We don't do any smarts around cancellations, or managing exceptions from
childen, because we don't need that for our use-case.
"""
import threading
from types import TracebackType
from typing import List, Type


class Nursery:
    def __init__(self) -> None:
        self._threads: List[threading.Thread] = []

    def __enter__(self) -> "Nursery":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        for thread in self._threads:
            thread.start()
        for thread in self._threads:
            thread.join()

    def start_soon(self, func, *args):
        thread = threading.Thread(target=func, args=args)
        self._threads.append(thread)


def open_nursery() -> Nursery:
    return Nursery()
