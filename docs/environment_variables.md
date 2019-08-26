Environment Variables
=====================

The HTTPX library can be configured via environment variables.
Here is a list of environment variables that HTTPX recognizes
and what function they serve:

`HTTPX_DEBUG`
-----------

Valid values: `1`, `true`

If this environment variable is set to `1` or `true` then
logging will be turned on by default to stderr about low-level
details of the HTTP request and responses being sent and received.

This can help you debug issues and see what's exactly being sent
over the wire and to which location.

Example:

```python
# test_script.py

import httpx
client = httpx.Client()
client.request("GET", "https://google.com")
```

```console
user@host:~$ HTTPX_DEBUG=1 python test_script.py
20:54:17.585 - httpx.dispatch.connection_pool - acquire_connection origin=Origin(scheme='https' host='www.google.com' port=443)
20:54:17.585 - httpx.dispatch.connection_pool - new_connection connection=HTTPConnection(origin=Origin(scheme='https' host='www.google.com' port=443))
20:54:17.590 - httpx.dispatch.connection - start_connect host='www.google.com' port=443 timeout=TimeoutConfig(timeout=5.0)
20:54:17.651 - httpx.dispatch.connection - connected http_version='HTTP/2'
20:54:17.651 - httpx.dispatch.http2 - send_headers stream_id=1 headers=[(b':method', b'GET'), (b':authority', b'www.google.com'), ...]
20:54:17.652 - httpx.dispatch.http2 - end_stream stream_id=1
20:54:17.681 - httpx.dispatch.http2 - receive_event stream_id=0 event=<RemoteSettingsChanged changed_settings:{...}>
20:54:17.681 - httpx.dispatch.http2 - receive_event stream_id=0 event=<WindowUpdated stream_id:0, delta:983041>
20:54:17.682 - httpx.dispatch.http2 - receive_event stream_id=0 event=<SettingsAcknowledged changed_settings:{}>
20:54:17.739 - httpx.dispatch.http2 - receive_event stream_id=1 event=<ResponseReceived stream_id:1, headers:[(b':status', b'200'), ...]>
20:54:17.741 - httpx.dispatch.http2 - receive_event stream_id=1 event=<DataReceived stream_id:1, flow_controlled_length:5224 data:>
20:54:17.742 - httpx.dispatch.http2 - receive_event stream_id=1 event=<DataReceived stream_id:1, flow_controlled_length:59, data:>
20:54:17.742 - httpx.dispatch.http2 - receive_event stream_id=1 event=<StreamEnded stream_id:1>
20:54:17.742 - httpx.dispatch.http2 - receive_event stream_id=0 event=<PingReceived ping_data:0000000000000000>
20:54:17.743 - httpx.dispatch.connection_pool - release_connection connection=HTTPConnection(origin=Origin(scheme='https' host='www.google.com' port=443))
```
