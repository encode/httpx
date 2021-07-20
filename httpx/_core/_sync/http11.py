import enum
import time
from types import TracebackType
from typing import Iterator, Callable, List, Optional, Tuple, Type, Union

import h11

from ..backends.base import NetworkStream
from ..base import (
    ByteStream,
    ConnectionNotAvailable,
    Origin,
    RawRequest,
    RawResponse,
)
from ..synchronization import Lock
from .interfaces import ConnectionInterface

H11Event = Union[
    h11.Request,
    h11.Response,
    h11.InformationalResponse,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


class HTTPConnectionState(enum.IntEnum):
    NEW = 0
    ACTIVE = 1
    IDLE = 2
    CLOSED = 3


class HTTP11Connection(ConnectionInterface):
    READ_NUM_BYTES = 64 * 1024

    def __init__(
        self, origin: Origin, stream: NetworkStream, keepalive_expiry: float = None
    ) -> None:
        self._origin = origin
        self._network_stream = stream
        self._keepalive_expiry: Optional[float] = keepalive_expiry
        self._expire_at: Optional[float] = None
        self._connection_close = False
        self._state = HTTPConnectionState.NEW
        self._state_lock = Lock()
        self._request_count = 0
        self._h11_state = h11.Connection(our_role=h11.CLIENT)

    def handle_request(self, request: RawRequest) -> RawResponse:
        with self._state_lock:
            if self._state in (HTTPConnectionState.NEW, HTTPConnectionState.IDLE):
                self._request_count += 1
                self._state = HTTPConnectionState.ACTIVE
                self._expire_at = None
            else:
                raise ConnectionNotAvailable()

        try:
            self._send_request_headers(request)
            self._send_request_body(request)
            (
                http_version,
                status_code,
                reason_phrase,
                headers,
            ) = self._receive_response_headers()
            return RawResponse(
                status=status_code,
                headers=headers,
                stream=HTTPConnectionByteStream(
                    iterator=self._receive_response_body(),
                    close_func=self._response_closed,
                ),
                extensions={
                    "http_version": http_version,
                    "reason_phrase": reason_phrase,
                },
            )
        except BaseException as exc:
            self.close()
            raise exc

    # Sending the request...

    def _send_request_headers(self, request: RawRequest) -> None:
        event = h11.Request(
            method=request.method, target=request.url.target, headers=request.headers
        )
        self._send_event(event)

    def _send_request_body(self, request: RawRequest) -> None:
        assert isinstance(request.stream, ByteStream)
        for chunk in request.stream:
            event = h11.Data(data=chunk)
            self._send_event(event)

        event = h11.EndOfMessage()
        self._send_event(event)

    def _send_event(self, event: H11Event) -> None:
        bytes_to_send = self._h11_state.send(event)
        self._network_stream.write(bytes_to_send)

    # Receiving the response...

    def _receive_response_headers(
        self,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]]]:
        while True:
            event = self._receive_event()
            if isinstance(event, h11.Response):
                break

        http_version = b"HTTP/" + event.http_version

        # h11 version 0.11+ supports a `raw_items` interface to get the
        # raw header casing, rather than the enforced lowercase headers.
        headers = event.headers.raw_items()

        return http_version, event.status_code, event.reason, headers

    def _receive_response_body(self) -> Iterator[bytes]:
        while True:
            event = self._receive_event()
            if isinstance(event, h11.Data):
                yield bytes(event.data)
            elif isinstance(event, (h11.EndOfMessage, h11.PAUSED)):
                break

    def _receive_event(self) -> H11Event:
        while True:
            event = self._h11_state.next_event()

            if event is h11.NEED_DATA:
                data = self._network_stream.read(self.READ_NUM_BYTES)
                self._h11_state.receive_data(data)
            else:
                return event

    def _response_closed(self) -> None:
        with self._state_lock:
            if (
                self._h11_state.our_state is h11.DONE
                and self._h11_state.their_state is h11.DONE
            ):
                self._state = HTTPConnectionState.IDLE
                self._h11_state.start_next_cycle()
                if self._keepalive_expiry is not None:
                    now = time.monotonic()
                    self._expire_at = now + self._keepalive_expiry
            else:
                self.close()

    # Once the connection is no longer required...

    def close(self) -> None:
        # Note that this method unilaterally closes the connection, and does
        # not have any kind of locking in place around it.
        # For task-safe/thread-safe operations call into 'attempt_close' instead.
        self._state = HTTPConnectionState.CLOSED
        self._network_stream.close()

    # The ConnectionInterface methods provide information about the state of
    # the connection, allowing for a connection pooling implementation to
    # determine when to reuse and when to close the connection...

    def get_origin(self) -> Origin:
        return self._origin

    def is_available(self) -> bool:
        # Note that HTTP/1.1 connections in the "NEW" state are not treated as
        # being "available". The control flow which created the connection will
        # be able to send an outgoing request, but the connection will not be
        # acquired from the connection pool for any other request.
        return self._state == HTTPConnectionState.IDLE

    def has_expired(self) -> bool:
        now = time.monotonic()
        return self._expire_at is not None and now > self._expire_at

    def is_idle(self) -> bool:
        return self._state == HTTPConnectionState.IDLE

    def is_closed(self) -> bool:
        return self._state == HTTPConnectionState.CLOSED

    def attempt_close(self) -> bool:
        with self._state_lock:
            if self._state in (HTTPConnectionState.NEW, HTTPConnectionState.IDLE):
                self.close()
                return True
        return False

    def info(self) -> str:
        origin = str(self._origin)
        return f"{origin!r}, HTTP/1.1, {self._state.name}, Request Count: {self._request_count}"

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} [{self._state.name}, "
            f"Request Count: {self._request_count}]>"
        )

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    def __enter__(self) -> "HTTP11Connection":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()


class HTTPConnectionByteStream(ByteStream):
    def __init__(self, iterator: Iterator[bytes], close_func: Callable):
        self._aiterator = iterator
        self._aclose_func = close_func

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self._aiterator:
            yield chunk

    def close(self) -> None:
        self._aclose_func()
