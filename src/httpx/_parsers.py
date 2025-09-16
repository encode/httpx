import enum

from ._streams import Stream

__all__ = ['HTTPParser', 'Mode', 'ProtocolError']


# TODO...

# * Upgrade
# * CONNECT

# * Support 'Expect: 100 Continue'
# * Add 'Error' state transitions
# * Add tests to trickle data
# * Add type annotations

# * Optional... HTTP/1.0 support
# * Read trailing headers on Transfer-Encoding: chunked. Not just '\r\n'.
# * When writing Transfer-Encoding: chunked, split large writes into buffer size.
# * When reading Transfer-Encoding: chunked, handle incomplete reads from large chunk sizes.
# * .read() doesn't document if will always return maximum available.

# * validate method, target, protocol in request line
# * validate protocol, status_code, reason_phrase in response line
# * validate name, value on headers


class State(enum.Enum):
    WAIT = 0
    SEND_METHOD_LINE = 1
    SEND_STATUS_LINE = 2
    SEND_HEADERS = 3
    SEND_BODY = 4
    RECV_METHOD_LINE = 5
    RECV_STATUS_LINE = 6
    RECV_HEADERS = 7
    RECV_BODY = 8
    DONE = 9
    CLOSED = 10


class Mode(enum.Enum):
    CLIENT = 0
    SERVER = 1


# The usual transitions will be...

# IDLE, IDLE
# SEND_HEADERS, IDLE
# SEND_BODY, IDLE
# DONE, IDLE
# DONE, SEND_HEADERS
# DONE, SEND_BODY
# DONE, DONE

# Then either back to IDLE, IDLE
# or move to CLOSED, CLOSED

# 1. It is also valid for the server to start
#    sending the response without waiting for the
#    complete request.
# 2. 1xx status codes are interim states, and
#    transition from SEND_HEADERS back to IDLE
# 3. ...

class ProtocolError(Exception):
    pass


class HTTPParser:
    """
    Usage...

    client = HTTPParser(writer, reader)
    client.send_method_line()
    client.send_headers()
    client.send_body()
    client.recv_status_line()
    client.recv_headers()
    client.recv_body()
    client.complete()
    client.close()
    """
    def __init__(self, stream: Stream, mode: str) -> None:
        self.stream = stream
        self.parser = ReadAheadParser(stream)
        self.mode = {'CLIENT': Mode.CLIENT, 'SERVER': Mode.SERVER}[mode]

        # Track state...
        if self.mode == Mode.CLIENT:
            self.send_state: State = State.SEND_METHOD_LINE
            self.recv_state: State = State.WAIT
        else:
            self.recv_state = State.RECV_METHOD_LINE
            self.send_state = State.WAIT

        # Track message framing...
        self.send_content_length: int | None = 0
        self.recv_content_length: int | None = 0
        self.send_seen_length = 0
        self.recv_seen_length = 0

        # Track connection keep alive...
        self.send_keep_alive = True
        self.recv_keep_alive = True

        # Special states...
        self.processing_1xx = False

    def send_method_line(self, method: bytes, target: bytes, protocol: bytes) -> None:
        """
        Send the initial request line:

        >>> p.send_method_line(b'GET', b'/', b'HTTP/1.1')

        Sending state will switch to SEND_HEADERS state.
        """
        if self.send_state != State.SEND_METHOD_LINE:
            msg = f"Called 'send_method_line' in invalid state {self.send_state}"
            raise ProtocolError(msg)

        # Send initial request line, eg. "GET / HTTP/1.1"
        if protocol != b'HTTP/1.1':
            raise ProtocolError("Sent unsupported protocol version")
        data = b" ".join([method, target, protocol]) + b"\r\n"
        self.stream.write(data)

        self.send_state = State.SEND_HEADERS
        self.recv_state = State.RECV_STATUS_LINE

    def send_status_line(self, protocol: bytes, status_code: int, reason: bytes) -> None:
        """
        Send the initial response line:

        >>> p.send_method_line(b'HTTP/1.1', 200, b'OK')

        Sending state will switch to SEND_HEADERS state.
        """
        if self.send_state != State.SEND_STATUS_LINE:
            msg = f"Called 'send_status_line' in invalid state {self.send_state}"
            raise ProtocolError(msg)

        # Send initial request line, eg. "GET / HTTP/1.1"
        if protocol != b'HTTP/1.1':
            raise ProtocolError("Sent unsupported protocol version")
        status_code_bytes = str(status_code).encode('ascii')
        data = b" ".join([protocol, status_code_bytes, reason]) + b"\r\n"
        self.stream.write(data)

        self.send_state = State.SEND_HEADERS

    def send_headers(self, headers: list[tuple[bytes, bytes]]) -> None:
        """
        Send the request headers:

        >>> p.send_headers([(b'Host', b'www.example.com')])

        Sending state will switch to SEND_BODY state.
        """
        if self.send_state != State.SEND_HEADERS:
            msg = f"Called 'send_headers' in invalid state {self.send_state}"
            raise ProtocolError(msg)

        # Update header state
        seen_host = False
        for name, value in headers:
            lname = name.lower()
            if lname == b'host':
                seen_host = True
            elif lname == b'content-length':
                self.send_content_length = bounded_int(
                    value,
                    max_digits=20,
                    exc_text="Sent invalid Content-Length"
                )
            elif lname == b'connection' and value == b'close':
                self.send_keep_alive = False
            elif lname == b'transfer-encoding' and value == b'chunked':
                self.send_content_length = None

        if self.mode == Mode.CLIENT and not seen_host:
            raise ProtocolError("Request missing 'Host' header")

        # Send request headers
        lines = [name + b": " + value + b"\r\n" for name, value in headers]
        data = b"".join(lines) + b"\r\n"
        self.stream.write(data)

        self.send_state = State.SEND_BODY

    def send_body(self, body: bytes) -> None:
        """
        Send the request body. An empty bytes argument indicates the end of the stream:

        >>> p.send_body(b'')

        Sending state will switch to DONE.
        """
        if self.send_state != State.SEND_BODY:
            msg = f"Called 'send_body' in invalid state {self.send_state}"
            raise ProtocolError(msg)

        if self.send_content_length is None:
            # Transfer-Encoding: chunked
            self.send_seen_length += len(body)
            marker = f'{len(body):x}\r\n'.encode('ascii')
            self.stream.write(marker + body + b'\r\n')

        else:
            # Content-Length: xxx
            self.send_seen_length += len(body)
            if self.send_seen_length > self.send_content_length:
                msg = 'Too much data sent for declared Content-Length'
                raise ProtocolError(msg)
            if self.send_seen_length < self.send_content_length and body == b'':
                msg = 'Not enough data sent for declared Content-Length'
                raise ProtocolError(msg)
            if body:
                self.stream.write(body)

        if body == b'':
            # Handle body close
            self.send_state = State.DONE

    def recv_method_line(self) -> tuple[bytes, bytes, bytes]:
        """
        Receive the initial request method line:

        >>> method, target, protocol = p.recv_status_line()

        Receive state will switch to RECV_HEADERS.
        """
        if self.recv_state != State.RECV_METHOD_LINE:
            msg = f"Called 'recv_method_line' in invalid state {self.recv_state}"
            raise ProtocolError(msg)

        # Read initial response line, eg. "GET / HTTP/1.1"
        exc_text = "reading request method line"
        line = self.parser.read_until(b"\r\n", max_size=4096, exc_text=exc_text)
        method, target, protocol = line.split(b" ", 2)
        if protocol != b'HTTP/1.1':
            raise ProtocolError("Received unsupported protocol version")

        self.recv_state = State.RECV_HEADERS
        self.send_state = State.SEND_STATUS_LINE
        return method, target, protocol

    def recv_status_line(self) -> tuple[bytes, int, bytes]:
        """
        Receive the initial response status line:

        >>> protocol, status_code, reason_phrase = p.recv_status_line()

        Receive state will switch to RECV_HEADERS.
        """
        if self.recv_state != State.RECV_STATUS_LINE:
            msg = f"Called 'recv_status_line' in invalid state {self.recv_state}"
            raise ProtocolError(msg)

        # Read initial response line, eg. "HTTP/1.1 200 OK"
        exc_text = "reading response status line"
        line = self.parser.read_until(b"\r\n", max_size=4096, exc_text=exc_text)
        protocol, status_code_str, reason_phrase = line.split(b" ", 2)
        if protocol != b'HTTP/1.1':
            raise ProtocolError("Received unsupported protocol version")

        status_code = bounded_int(
            status_code_str,
            max_digits=3,
            exc_text="Received invalid status code"
        )
        if status_code < 100:
            raise ProtocolError("Received invalid status code")
        # 1xx status codes preceed the final response status code
        self.processing_1xx = status_code < 200

        self.recv_state = State.RECV_HEADERS
        return protocol, status_code, reason_phrase

    def recv_headers(self) -> list[tuple[bytes, bytes]]:
        """
        Receive the response headers:

        >>> headers = p.recv_status_line()

        Receive state will switch to RECV_BODY by default.
        Receive state will revert to RECV_STATUS_CODE for interim 1xx responses.
        """
        if self.recv_state != State.RECV_HEADERS:
            msg = f"Called 'recv_headers' in invalid state {self.recv_state}"
            raise ProtocolError(msg)

        # Read response headers
        headers = []
        exc_text = "reading response headers"
        while line := self.parser.read_until(b"\r\n", max_size=4096, exc_text=exc_text):
            name, value = line.split(b":", 1)
            value = value.strip(b" ")
            headers.append((name, value))

        # Update header state
        seen_host = False
        for name, value in headers:
            lname = name.lower()
            if lname == b'host':
                seen_host = True
            elif lname == b'content-length':
                self.recv_content_length = bounded_int(
                    value,
                    max_digits=20,
                    exc_text="Received invalid Content-Length"
                )
            elif lname == b'connection' and value == b'close':
                self.recv_keep_alive = False
            elif lname == b'transfer-encoding' and value == b'chunked':
                self.recv_content_length = None

        if self.mode == Mode.SERVER and not seen_host:
            raise ProtocolError("Request missing 'Host' header")

        if self.processing_1xx:
            # 1xx status codes preceed the final response status code
            self.processing_1xx = False
            self.recv_state = State.RECV_STATUS_LINE
        else:
            self.recv_state = State.RECV_BODY
        return headers

    def recv_body(self) -> bytes:
        """
        Receive the response body. An empty byte string indicates the end of the stream:

        >>> buffer = bytearray()
        >>> while body := p.recv_body()
        >>>     buffer.extend(body)

        The server will switch to DONE.
        """
        if self.recv_state != State.RECV_BODY:
            msg = f"Called 'recv_body' in invalid state {self.recv_state}"
            raise ProtocolError(msg)

        if self.recv_content_length is None:
            # Transfer-Encoding: chunked
            exc_text = 'reading chunk size'
            line = self.parser.read_until(b"\r\n", max_size=4096, exc_text=exc_text)
            sizestr, _, _ = line.partition(b";")

            exc_text = "Received invalid chunk size"
            size = bounded_hex(sizestr, max_digits=8, exc_text=exc_text)
            if size > 0:
                body = self.parser.read(size=size)
                exc_text = 'reading chunk data'
                self.parser.read_until(b"\r\n", max_size=2, exc_text=exc_text)
                self.recv_seen_length += len(body)
            else:
                body = b''
                exc_text = 'reading chunk termination'
                self.parser.read_until(b"\r\n", max_size=2, exc_text=exc_text)

        else:
            # Content-Length: xxx
            remaining = self.recv_content_length - self.recv_seen_length
            size = min(remaining, 4096)
            body = self.parser.read(size=size)
            self.recv_seen_length += len(body)
            if self.recv_seen_length < self.recv_content_length and body == b'':
                msg = 'Not enough data received for declared Content-Length'
                raise ProtocolError(msg)

        if body == b'':
            # Handle body close
            self.recv_state = State.DONE
        return body

    def complete(self):
        is_fully_complete = self.send_state == State.DONE and self.recv_state == State.DONE
        is_keepalive = self.send_keep_alive and self.recv_keep_alive

        if not (is_fully_complete and is_keepalive):
            self.close()
            return

        if self.mode == Mode.CLIENT:
            self.send_state = State.SEND_METHOD_LINE
            self.recv_state = State.WAIT
        else:
            self.recv_state = State.RECV_METHOD_LINE
            self.send_state = State.WAIT

        self.send_content_length = 0
        self.recv_content_length = 0
        self.send_seen_length = 0
        self.recv_seen_length = 0
        self.send_keep_alive = True
        self.recv_keep_alive = True
        self.processing_1xx = False

    def close(self):
        if self.send_state != State.CLOSED:
            self.send_state = State.CLOSED
            self.recv_state = State.CLOSED
            self.stream.close()

    def is_idle(self) -> bool:
        return (
            self.send_state == State.SEND_METHOD_LINE or
            self.recv_state == State.RECV_METHOD_LINE
        )

    def is_closed(self) -> bool:
        return self.send_state == State.CLOSED

    def description(self) -> str:
        return {
            State.SEND_METHOD_LINE: "idle",
            State.CLOSED: "closed",
        }.get(self.send_state, "active")

    def __repr__(self) -> str:
        cl_state = self.send_state.name
        sr_state = self.recv_state.name
        detail = f"client {cl_state}, server {sr_state}"
        return f'<HTTPParser [{detail}]>'


class ReadAheadParser:
    """
    A buffered I/O stream, with methods for read-ahead parsing.
    """
    def __init__(self, stream: Stream) -> None:
        self._buffer = b''
        self._stream = stream
        self._chunk_size = 4096

    def _read_some(self) -> bytes:
        if self._buffer:
            ret, self._buffer = self._buffer, b''
            return ret
        return self._stream.read(self._chunk_size)

    def _push_back(self, buffer):
        assert self._buffer == b''
        self._buffer = buffer

    def read(self, size: int) -> bytes:
        """
        Read and return up to 'size' bytes from the stream, with I/O buffering provided.

        * Returns b'' to indicate connection close.
        """
        buffer = bytearray()
        while len(buffer) < size:
            chunk = self._read_some()
            if not chunk:
                break
            buffer.extend(chunk)

        if len(buffer) > size:
            buffer, push_back = buffer[:size], buffer[size:]
            self._push_back(bytes(push_back))
        return bytes(buffer)

    def read_until(self, marker: bytes, max_size: int, exc_text: str) -> bytes:
        """
        Read and return bytes from the stream, delimited by marker.

        * The marker is not included in the return bytes.
        * The marker is consumed from the I/O stream.
        * Raises `ProtocolError` if the stream closes before a marker occurance.
        * Raises `ProtocolError` if marker did not occur within 'max_size + len(marker)' bytes.
        """
        buffer = bytearray()
        while len(buffer) <= max_size:
            chunk = self._read_some()
            if not chunk:
                # stream closed before marker found.
                raise ProtocolError(f"Stream closed early {exc_text}")
            start_search = max(len(buffer) - len(marker), 0)
            buffer.extend(chunk)
            index = buffer.find(marker, start_search)

            if index > max_size:
                # marker was found, though 'max_size' exceeded.
                raise ProtocolError(f"Exceeded maximum size {exc_text}")
            elif index >= 0:
                endindex = index + len(marker)
                self._push_back(bytes(buffer[endindex:]))
                return bytes(buffer[:index])

        raise ProtocolError(f"Exceeded maximum size {exc_text}")


def bounded_int(intstr: bytes, max_digits: int, exc_text: str):
    if len(intstr) > max_digits:
        # Length of bytestring exceeds maximum.
        raise ProtocolError(exc_text)
    if len(intstr.strip(b'0123456789')) != 0:
        # Contains invalid characters.
        raise ProtocolError(exc_text)

    return int(intstr)


def bounded_hex(hexstr: bytes, max_digits: int, exc_text: str):
    if len(hexstr) > max_digits:
        # Length of bytestring exceeds maximum.
        raise ProtocolError(exc_text)
    if len(hexstr.strip(b'0123456789abcdefABCDEF')) != 0:
        # Contains invalid characters.
        raise ProtocolError(exc_text)

    return int(hexstr, base=16)
