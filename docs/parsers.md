# Parsers

### Client

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
stream = httpx.DuplexStream(
    b'HTTP/1.1 200 OK\r\n'
    b'Content-Length: 23\r\n'
    b'Content-Type: application/json\r\n'
    b'\r\n'
    b'{"msg": "hello, world"}'
)
p = ahttpx.HTTPParser(stream, mode='CLIENT')

# Send the request...
p.send_method_line(b'GET', b'/', b'HTTP/1.1')
p.send_headers([(b'Host', b'www.example.com')])
p.send_body(b'')

# Receive the response...
protocol, code, reason_phase = p.recv_status_line()
headers = p.recv_headers()
body = b''
while buffer := p.recv_body():
    body += buffer
```

```{ .python .ahttpx .hidden }
stream = ahttpx.DuplexStream(
    b'HTTP/1.1 200 OK\r\n'
    b'Content-Length: 23\r\n'
    b'Content-Type: application/json\r\n'
    b'\r\n'
    b'{"msg": "hello, world"}'
)
p = ahttpx.HTTPParser(stream, mode='CLIENT')

# Send the request...
await p.send_method_line(b'GET', b'/', b'HTTP/1.1')
await p.send_headers([(b'Host', b'www.example.com')])
await p.send_body(b'')

# Receive the response...
protocol, code, reason_phase = await p.recv_status_line()
headers = await p.recv_headers()
body = b''
while buffer := await p.recv_body():
    body += buffer
```

### Server

<div class="tabs"><a onclick="httpx()" class="httpx">httpx</a> <a onclick="ahttpx()" class="ahttpx hidden">ahttpx</a></div>

```{ .python .httpx }
stream = httpx.DuplexStream(
    b'GET / HTTP/1.1\r\n'
    b'Host: www.example.com\r\n'
    b'\r\n'
)
p = httpx.HTTPParser(stream, mode='SERVER')

# Receive the request...
method, target, protocol = p.recv_method_line()
headers = p.recv_headers()
body = b''
while buffer := p.recv_body():
    body += buffer

# Send the response...
p.send_status_line(b'HTTP/1.1', 200, b'OK')
p.send_headers([
    (b'Content-Length', b'23'),
    (b'Content-Type', b'application/json')
])
p.send_body(b'{"msg": "hello, world"}')
p.send_body(b'')
```

```{ .python .ahttpx .hidden }
stream = ahttpx.DuplexStream(
    b'GET / HTTP/1.1\r\n'
    b'Host: www.example.com\r\n'
    b'\r\n'
)
p = ahttpx.HTTPParser(stream, mode='SERVER')

# Receive the request...
method, target, protocol = await p.recv_method_line()
headers = await p.recv_headers()
body = b''
while buffer := await p.recv_body():
    body += buffer

# Send the response...
await p.send_status_line(b'HTTP/1.1', 200, b'OK')
await p.send_headers([
    (b'Content-Length', b'23'),
    (b'Content-Type', b'application/json')
])
await p.send_body(b'{"msg": "hello, world"}')
await p.send_body(b'')
```

---

<span class="link-prev">← [Connections](connections.md)</span>
<span class="link-next">[Low Level Networking](networking.md) →</span>
