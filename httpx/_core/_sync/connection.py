from types import TracebackType
from typing import List, Optional, Type

from ..backends.base import NetworkBackend
from ..backends.sync import SyncBackend
from ..base import ConnectionNotAvailable, Origin, RawRequest, RawResponse
from ..synchronization import Lock
from .http11 import HTTP11Connection
from .interfaces import ConnectionInterface


class HTTPConnection(ConnectionInterface):
    def __init__(
        self,
        origin: Origin,
        keepalive_expiry: float = None,
        buffer: List[bytes] = None,
        network_backend: NetworkBackend = None,
    ) -> None:
        self._origin = origin
        self._keepalive_expiry = keepalive_expiry
        self._network_backend: NetworkBackend = (
            SyncBackend() if network_backend is None else network_backend
        )
        self._connection: Optional[ConnectionInterface] = None
        self._request_lock = Lock()

    def handle_request(self, request: RawRequest) -> RawResponse:
        with self._request_lock:
            if self._connection is None:
                origin = self._origin
                stream = self._network_backend.connect(origin=origin)
                self._connection = HTTP11Connection(
                    origin=origin,
                    stream=stream,
                    keepalive_expiry=self._keepalive_expiry,
                )
            elif not self._connection.is_available():
                raise ConnectionNotAvailable()

        return self._connection.handle_request(request)

    def attempt_aclose(self) -> bool:
        if self._connection is None:
            return False
        return self._connection.attempt_aclose()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()

    def get_origin(self) -> Origin:
        return self._origin

    def is_available(self) -> bool:
        if self._connection is None:
            return True
        return self._connection.is_available()

    def has_expired(self) -> bool:
        if self._connection is None:
            return False
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        if self._connection is None:
            return False
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        if self._connection is None:
            return False
        return self._connection.is_closed()

    def info(self) -> str:
        if self._connection is None:
            return "CONNECTING"
        return self._connection.info()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    def __enter__(self) -> "HTTPConnection":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()
