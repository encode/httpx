# Logging

If you need to inspect the internal behaviour of `httpx`, you can use Python's standard logging to output information about the underlying network behaviour.

For example, the following configuration...

```python
import logging
import httpx

logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)

httpx.get("https://www.example.com")
```

Will send debug level output to the console, or wherever `stdout` is directed too...

```
DEBUG [2024-09-28 17:27:40] httpx - load_ssl_context verify=True cert=None
DEBUG [2024-09-28 17:27:40] httpx - load_verify_locations cafile='/Users/karenpetrosyan/oss/karhttpx/.venv/lib/python3.9/site-packages/certifi/cacert.pem'
DEBUG [2024-09-28 17:27:40] httpcore.connection - connect_tcp.started host='www.example.com' port=443 local_address=None timeout=5.0 socket_options=None
DEBUG [2024-09-28 17:27:41] httpcore.connection - connect_tcp.complete return_value=<httpcore._backends.sync.SyncStream object at 0x101f1e8e0>
DEBUG [2024-09-28 17:27:41] httpcore.connection - start_tls.started ssl_context=SSLContext(verify=True) server_hostname='www.example.com' timeout=5.0
DEBUG [2024-09-28 17:27:41] httpcore.connection - start_tls.complete return_value=<httpcore._backends.sync.SyncStream object at 0x1020f49a0>
DEBUG [2024-09-28 17:27:41] httpcore.http11 - send_request_headers.started request=<Request [b'GET']>
DEBUG [2024-09-28 17:27:41] httpcore.http11 - send_request_headers.complete
DEBUG [2024-09-28 17:27:41] httpcore.http11 - send_request_body.started request=<Request [b'GET']>
DEBUG [2024-09-28 17:27:41] httpcore.http11 - send_request_body.complete
DEBUG [2024-09-28 17:27:41] httpcore.http11 - receive_response_headers.started request=<Request [b'GET']>
DEBUG [2024-09-28 17:27:41] httpcore.http11 - receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Content-Encoding', b'gzip'), (b'Accept-Ranges', b'bytes'), (b'Age', b'407727'), (b'Cache-Control', b'max-age=604800'), (b'Content-Type', b'text/html; charset=UTF-8'), (b'Date', b'Sat, 28 Sep 2024 13:27:42 GMT'), (b'Etag', b'"3147526947+gzip"'), (b'Expires', b'Sat, 05 Oct 2024 13:27:42 GMT'), (b'Last-Modified', b'Thu, 17 Oct 2019 07:18:26 GMT'), (b'Server', b'ECAcc (dcd/7D43)'), (b'Vary', b'Accept-Encoding'), (b'X-Cache', b'HIT'), (b'Content-Length', b'648')])
INFO [2024-09-28 17:27:41] httpx - HTTP Request: GET https://www.example.com "HTTP/1.1 200 OK"
DEBUG [2024-09-28 17:27:41] httpcore.http11 - receive_response_body.started request=<Request [b'GET']>
DEBUG [2024-09-28 17:27:41] httpcore.http11 - receive_response_body.complete
DEBUG [2024-09-28 17:27:41] httpcore.http11 - response_closed.started
DEBUG [2024-09-28 17:27:41] httpcore.http11 - response_closed.complete
DEBUG [2024-09-28 17:27:41] httpcore.connection - close.started
DEBUG [2024-09-28 17:27:41] httpcore.connection - close.complete
```

Logging output includes information from both the high-level `httpx` logger, and the network-level `httpcore` logger, which can be configured separately.

For handling more complex logging configurations you might want to use the dictionary configuration style...

```python
import logging.config
import httpx

LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "http",
            "stream": "ext://sys.stderr"
        }
    },
    "formatters": {
        "http": {
            "format": "%(levelname)s [%(asctime)s] %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    'loggers': {
        'httpx': {
            'handlers': ['default'],
            'level': 'DEBUG',
        },
        'httpcore': {
            'handlers': ['default'],
            'level': 'DEBUG',
        },
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
httpx.get('https://www.example.com')
```

The exact formatting of the debug logging may be subject to change across different versions of `httpx` and `httpcore`. If you need to rely on a particular format it is recommended that you pin installation of these packages to fixed versions.