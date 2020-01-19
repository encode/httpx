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

        To dispatch a request, you should `yield` it, and prepare for either:

        * The client sending back a response.
        * An `HTTPError` being raised.

        In each case, decide whether to retry:

        * If so, continue yielding, unless a maximum number of retries was exceeded.
        In that case, raise a `TooManyRetries` exception.
        * Otherwise, `return`, or `raise` the exception.
        """
        raise NotImplementedError  # pragma: no cover


class DontRetry(RetryLimits):
    def __eq__(self, other: typing.Any) -> bool:
        return type(other) == DontRetry

    def retry_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        # Send the initial request, and never retry.
        # NOTE: don't raise a `TooManyRetries` exception because this should
        # really be a no-op implementation.
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

    def _should_retry_for_exception(self, exc: HTTPError) -> bool:
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
                # Failed to get a response.

                if not retries_left:
                    raise TooManyRetries(exc, request=request)

                if self._should_retry_for_exception(exc):
                    retries_left -= 1
                    continue

                # Raise the exception for other retry limits involved to handle,
                # or for bubbling up to the client.
                raise
            else:
                # We managed to get a response without connection/network
                # failures, so we're done here.
                return
