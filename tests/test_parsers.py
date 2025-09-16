import httpx
import pytest


class TrickleIO(httpx.Stream):
    def __init__(self, stream: httpx.Stream):
        self._stream = stream

    def read(self, size) -> bytes:
        return self._stream.read(1)

    def write(self, data: bytes) -> None:
        self._stream.write(data)
    
    def close(self) -> None:
        self._stream.close()


def test_parser():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"POST", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Content-Type", b"application/json"),
        (b"Content-Length", b"23"),
    ])
    p.send_body(b'{"msg": "hello, world"}')
    p.send_body(b'')

    assert stream.input_bytes() == (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )
    assert stream.output_bytes() == (
        b"POST / HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 23\r\n"
        b"\r\n"
        b'{"msg": "hello, world"}'
    )

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b'OK'
    assert headers == [
        (b'Content-Length', b'12'),
        (b'Content-Type', b'text/plain'),
    ]
    assert body == b'hello, world'
    assert terminator == b''

    assert not p.is_idle()
    p.complete()
    assert p.is_idle()


def test_parser_server():
    stream = httpx.DuplexStream(
        b"GET / HTTP/1.1\r\n"
        b"Host: www.example.com\r\n"
        b"\r\n"
    )

    p = httpx.HTTPParser(stream, mode='SERVER')
    method, target, protocol = p.recv_method_line()
    headers = p.recv_headers()
    body = p.recv_body()

    assert method == b'GET'
    assert target == b'/'
    assert protocol == b'HTTP/1.1'
    assert headers == [
        (b'Host', b'www.example.com'),
    ]
    assert body == b''

    p.send_status_line(b"HTTP/1.1", 200, b"OK")
    p.send_headers([
        (b"Content-Type", b"application/json"),
        (b"Content-Length", b"23"),
    ])
    p.send_body(b'{"msg": "hello, world"}')
    p.send_body(b'')

    assert stream.input_bytes() == (
        b"GET / HTTP/1.1\r\n"
        b"Host: www.example.com\r\n"
        b"\r\n"
    )
    assert stream.output_bytes() == (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 23\r\n"
        b"\r\n"
        b'{"msg": "hello, world"}'
    )

    assert not p.is_idle()
    p.complete()
    assert p.is_idle()


def test_parser_trickle():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(TrickleIO(stream), mode='CLIENT')
    p.send_method_line(b"POST", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Content-Type", b"application/json"),
        (b"Content-Length", b"23"),
    ])
    p.send_body(b'{"msg": "hello, world"}')
    p.send_body(b'')

    assert stream.input_bytes() == (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )
    assert stream.output_bytes() == (
        b"POST / HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 23\r\n"
        b"\r\n"
        b'{"msg": "hello, world"}'
    )

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b'OK'
    assert headers == [
        (b'Content-Length', b'12'),
        (b'Content-Type', b'text/plain'),
    ]
    assert body == b'hello, world'
    assert terminator == b''


def test_parser_transfer_encoding_chunked():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"c\r\n"
        b"hello, world\r\n"
        b"0\r\n\r\n"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"POST", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Content-Type", b"application/json"),
        (b"Transfer-Encoding", b"chunked"),
    ])
    p.send_body(b'{"msg": "hello, world"}')
    p.send_body(b'')

    assert stream.input_bytes() == (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"c\r\n"
        b"hello, world\r\n"
        b"0\r\n\r\n"
    )
    assert stream.output_bytes() == (
        b"POST / HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Content-Type: application/json\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b'17\r\n'
        b'{"msg": "hello, world"}\r\n'
        b'0\r\n\r\n'
    )

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b'OK'
    assert headers == [
        (b'Content-Type', b'text/plain'),
        (b'Transfer-Encoding', b'chunked'),
    ]
    assert body == b'hello, world'
    assert terminator == b''


def test_parser_transfer_encoding_chunked_trickle():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"c\r\n"
        b"hello, world\r\n"
        b"0\r\n\r\n"
    )

    p = httpx.HTTPParser(TrickleIO(stream), mode='CLIENT')
    p.send_method_line(b"POST", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Content-Type", b"application/json"),
        (b"Transfer-Encoding", b"chunked"),
    ])
    p.send_body(b'{"msg": "hello, world"}')
    p.send_body(b'')

    assert stream.input_bytes() == (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"c\r\n"
        b"hello, world\r\n"
        b"0\r\n\r\n"
    )
    assert stream.output_bytes() == (
        b"POST / HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Content-Type: application/json\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b'17\r\n'
        b'{"msg": "hello, world"}\r\n'
        b'0\r\n\r\n'
    )

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b'OK'
    assert headers == [
        (b'Content-Type', b'text/plain'),
        (b'Transfer-Encoding', b'chunked'),
    ]
    assert body == b'hello, world'
    assert terminator == b''


def test_parser_repr():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 23\r\n"
        b"\r\n"
        b'{"msg": "hello, world"}'
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    assert repr(p) == "<HTTPParser [client SEND_METHOD_LINE, server WAIT]>"

    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    assert repr(p) == "<HTTPParser [client SEND_HEADERS, server RECV_STATUS_LINE]>"

    p.send_headers([(b"Host", b"example.com")])
    assert repr(p) == "<HTTPParser [client SEND_BODY, server RECV_STATUS_LINE]>"

    p.send_body(b'')
    assert repr(p) == "<HTTPParser [client DONE, server RECV_STATUS_LINE]>"

    p.recv_status_line()
    assert repr(p) == "<HTTPParser [client DONE, server RECV_HEADERS]>"

    p.recv_headers()
    assert repr(p) == "<HTTPParser [client DONE, server RECV_BODY]>"

    p.recv_body()
    assert repr(p) == "<HTTPParser [client DONE, server RECV_BODY]>"

    p.recv_body()
    assert repr(p) == "<HTTPParser [client DONE, server DONE]>"

    p.complete()
    assert repr(p) == "<HTTPParser [client SEND_METHOD_LINE, server WAIT]>"


def test_parser_invalid_transitions():
    stream = httpx.DuplexStream()

    with pytest.raises(httpx.ProtocolError):
        p = httpx.HTTPParser(stream, mode='CLIENT')
        p.send_method_line(b'GET', b'/', b'HTTP/1.1')
        p.send_method_line(b'GET', b'/', b'HTTP/1.1')

    with pytest.raises(httpx.ProtocolError):
        p = httpx.HTTPParser(stream, mode='CLIENT')
        p.send_headers([])

    with pytest.raises(httpx.ProtocolError):
        p = httpx.HTTPParser(stream, mode='CLIENT')
        p.send_body(b'')

    with pytest.raises(httpx.ProtocolError):
        reader = httpx.ByteStream(b'HTTP/1.1 200 OK\r\n')
        p = httpx.HTTPParser(stream, mode='CLIENT')
        p.recv_status_line()

    with pytest.raises(httpx.ProtocolError):
        p = httpx.HTTPParser(stream, mode='CLIENT')
        p.recv_headers()

    with pytest.raises(httpx.ProtocolError):
        p = httpx.HTTPParser(stream, mode='CLIENT')
        p.recv_body()


def test_parser_invalid_status_line():
    # ...
    stream = httpx.DuplexStream(b'...')

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    msg = 'Stream closed early reading response status line'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_status_line()

    # ...
    stream = httpx.DuplexStream(b'HTTP/1.1' + b'x' * 5000)

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    msg = 'Exceeded maximum size reading response status line'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_status_line()

    # ...
    stream = httpx.DuplexStream(b'HTTP/1.1' + b'x' * 5000 + b'\r\n')

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    msg = 'Exceeded maximum size reading response status line'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_status_line()


def test_parser_sent_unsupported_protocol():
    # Currently only HTTP/1.1 is supported.
    stream = httpx.DuplexStream()

    p = httpx.HTTPParser(stream, mode='CLIENT')
    msg = 'Sent unsupported protocol version'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.send_method_line(b"GET", b"/", b"HTTP/1.0")


def test_parser_recv_unsupported_protocol():
    # Currently only HTTP/1.1 is supported.
    stream = httpx.DuplexStream(b"HTTP/1.0 200 OK\r\n")

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    msg = 'Received unsupported protocol version'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_status_line()


def test_parser_large_body():
    body = b"x" * 6988

    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 6988\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n" + body
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    # Checkout our buffer sizes.
    p.recv_status_line()
    p.recv_headers()
    assert len(p.recv_body()) == 4096
    assert len(p.recv_body()) == 2892
    assert len(p.recv_body()) == 0


def test_parser_stream_large_body():
    body = b"x" * 6956

    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"1b2c\r\n" + body + b'\r\n0\r\n\r\n'
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    # Checkout our buffer sizes.
    p.recv_status_line()
    p.recv_headers()
    # assert len(p.recv_body()) == 4096
    # assert len(p.recv_body()) == 2860
    assert len(p.recv_body()) == 6956
    assert len(p.recv_body()) == 0


def test_parser_not_enough_data_received():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 188\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"truncated"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    # Checkout our buffer sizes.
    p.recv_status_line()
    p.recv_headers()
    p.recv_body()
    msg = 'Not enough data received for declared Content-Length'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_body()


def test_parser_not_enough_data_sent():
    stream = httpx.DuplexStream()

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"POST", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Content-Type", b"application/json"),
        (b"Content-Length", b"23"),
    ])
    p.send_body(b'{"msg": "too smol"}')
    msg = 'Not enough data sent for declared Content-Length'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.send_body(b'')


def test_parser_too_much_data_sent():
    stream = httpx.DuplexStream()

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"POST", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Content-Type", b"application/json"),
        (b"Content-Length", b"19"),
    ])
    msg = 'Too much data sent for declared Content-Length'
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.send_body(b'{"msg": "too chonky"}')


def test_parser_missing_host_header():
    stream = httpx.DuplexStream()

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    msg = "Request missing 'Host' header"
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.send_headers([])


def test_client_connection_close():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Connection", b"close"),
    ])
    p.send_body(b'')

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b"OK"
    assert headers == [
        (b'Content-Length', b'12'),
        (b'Content-Type', b'text/plain'),
    ]
    assert body == b"hello, world"
    assert terminator == b""

    assert repr(p) == "<HTTPParser [client DONE, server DONE]>"

    p.complete()
    assert repr(p) == "<HTTPParser [client CLOSED, server CLOSED]>"
    assert p.is_closed()


def test_server_connection_close():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b"OK"
    assert headers == [
        (b'Content-Length', b'12'),
        (b'Content-Type', b'text/plain'),
        (b'Connection', b'close'),
    ]
    assert body == b"hello, world"
    assert terminator == b""

    assert repr(p) == "<HTTPParser [client DONE, server DONE]>"
    p.complete()
    assert repr(p) == "<HTTPParser [client CLOSED, server CLOSED]>"


def test_invalid_status_code():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 99 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Connection", b"close"),
    ])
    p.send_body(b'')

    msg = "Received invalid status code"
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_status_line()


def test_1xx_status_code():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 103 Early Hints\r\n"
        b"Link: </style.css>; rel=preload; as=style\r\n"
        b"Link: </script.js>; rel=preload; as=script\r\n"
        b"\r\n"
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([(b"Host", b"example.com")])
    p.send_body(b'')

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()

    assert protocol == b'HTTP/1.1'
    assert code == 103
    assert reason_phase == b'Early Hints'
    assert headers == [
        (b'Link', b'</style.css>; rel=preload; as=style'),
        (b'Link', b'</script.js>; rel=preload; as=script'),
    ]

    protocol, code, reason_phase = p.recv_status_line()
    headers = p.recv_headers()
    body = p.recv_body()
    terminator = p.recv_body()

    assert protocol == b'HTTP/1.1'
    assert code == 200
    assert reason_phase == b"OK"
    assert headers == [
        (b'Content-Length', b'12'),
        (b'Content-Type', b'text/plain'),
    ]
    assert body == b"hello, world"
    assert terminator == b""


def test_received_invalid_content_length():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: -999\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"hello, world"
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Connection", b"close"),
    ])
    p.send_body(b'')

    p.recv_status_line()
    msg = "Received invalid Content-Length"
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_headers()


def test_sent_invalid_content_length():
    stream = httpx.DuplexStream()

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    msg = "Sent invalid Content-Length"
    with pytest.raises(httpx.ProtocolError, match=msg):
        # Limited to 20 digits.
        # 100 million terabytes should be enough for anyone.
        p.send_headers([
            (b"Host", b"example.com"),
            (b"Content-Length", b"100000000000000000000"),
        ])


def test_received_invalid_characters_in_chunk_size():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"0xFF\r\n..."
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Connection", b"close"),
    ])
    p.send_body(b'')

    p.recv_status_line()
    p.recv_headers()
    msg = "Received invalid chunk size"
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_body()


def test_received_oversized_chunk():
    stream = httpx.DuplexStream(
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"FFFFFFFFFF\r\n..."
    )

    p = httpx.HTTPParser(stream, mode='CLIENT')
    p.send_method_line(b"GET", b"/", b"HTTP/1.1")
    p.send_headers([
        (b"Host", b"example.com"),
        (b"Connection", b"close"),
    ])
    p.send_body(b'')

    p.recv_status_line()
    p.recv_headers()
    msg = "Received invalid chunk size"
    with pytest.raises(httpx.ProtocolError, match=msg):
        p.recv_body()
