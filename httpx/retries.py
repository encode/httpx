import typing

from .exceptions import (
    ConnectTimeout,
    HTTPError,
    NetworkError,
    PoolTimeout,
    TooManyRetries,
)
from .models import Request, Response
from .utils import get_logger

logger = get_logger(__name__)


class RetryLimits:
    """
    Base class for retry limiting policies.
    """

    def retry_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        """
        Execute the retry flow.

        To dispatch a request, you should `yield` it, and prepare for either
        getting a response, or an `HTTPError` being raised.

        In each case, decide whether to retry:

        * If so, continue yielding, unless a maximum number of retries was exceeded.
        In that case, raise a `TooManyRetries` exception.
        * Otherwise, `return`, or `raise` the exception.
        """
        raise NotImplementedError  # pragma: no cover

    def __or__(self, other: typing.Any) -> "RetryLimits":
        if not isinstance(other, RetryLimits):
            raise NotImplementedError  # pragma: no cover
        return _OrRetries(self, other)


class _OrRetries(RetryLimits):
    """
    Helper for composing retry limits.
    """

    def __init__(self, left: RetryLimits, right: RetryLimits) -> None:
        self.left = left
        self.right = right

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, _OrRetries)
            and self.left == other.left
            and self.right == other.right
        )

    def retry_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        left_flow = self.left.retry_flow(request)
        right_flow = self.right.retry_flow(request)

        request = next(left_flow)
        request = next(right_flow)

        while True:
            try:
                response = yield request
            except HTTPError as exc:
                try:
                    request = left_flow.throw(type(exc), exc, exc.__traceback__)
                except TooManyRetries:
                    raise
                except HTTPError:
                    try:
                        request = right_flow.throw(type(exc), exc, exc.__traceback__)
                    except TooManyRetries:
                        raise
                    except HTTPError:
                        raise
                    else:
                        continue
                else:
                    continue
            else:
                try:
                    request = left_flow.send(response)
                except TooManyRetries:
                    raise
                except StopIteration:
                    try:
                        request = right_flow.send(response)
                    except TooManyRetries:
                        raise
                    except StopIteration:
                        return
                    else:
                        continue
                else:
                    continue


class DontRetry(RetryLimits):
    def __eq__(self, other: typing.Any) -> bool:
        return type(other) == DontRetry

    def retry_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        # Send the initial request, and never retry.
        # Don't raise a `TooManyRetries` exception because this should really be
        # a no-op implementation.
        yield request


class RetryOnConnectionFailures(RetryLimits):
    """
    Retry when failing to establish a connection, or when a network
    error occurred.
    """

    _RETRYABLE_EXCEPTIONS: typing.Sequence[typing.Type[HTTPError]] = (
        ConnectTimeout,
        PoolTimeout,
        NetworkError,
    )
    _RETRYABLE_METHODS: typing.Container[str] = frozenset(
        ("HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE")
    )

    def __init__(self, limit: int = 3) -> None:
        assert limit >= 0
        self.limit = limit

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, RetryOnConnectionFailures) and self.limit == other.limit
        )

    def _should_retry_on_exception(self, exc: HTTPError) -> bool:
        for exc_cls in self._RETRYABLE_EXCEPTIONS:
            if isinstance(exc, exc_cls):
                break
        else:
            logger.debug(f"not_retryable exc_type={type(exc)}")
            return False

        assert exc.request is not None
        method = exc.request.method.upper()
        if method not in self._RETRYABLE_METHODS:
            logger.debug(f"not_retryable method={method!r}")
            return False

        return True

    def retry_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        retries_left = self.limit

        while True:
            try:
                _ = yield request
            except HTTPError as exc:
                # Failed to get a response...

                if not retries_left:
                    raise TooManyRetries(exc, request=request)

                if self._should_retry_on_exception(exc):
                    retries_left -= 1
                    continue

                # Raise the exception for other retry limits involved to handle,
                # or for bubbling up to the client.
                raise
            else:
                # We managed to get a response without connection/network
                # failures, so we're done here.
                return
