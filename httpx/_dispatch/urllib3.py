import math
import socket
import ssl
from typing import Dict, Iterator, List, Optional, Tuple, Union

import httpcore
import urllib3
from urllib3.exceptions import MaxRetryError, SSLError

from .._config import DEFAULT_POOL_LIMITS, PoolLimits, Proxy, SSLConfig
from .._content_streams import ByteStream, IteratorStream
from .._types import CertTypes, VerifyTypes
from .._utils import as_network_error


class URLLib3Dispatcher(httpcore.SyncHTTPTransport):
    def __init__(
        self,
        *,
        proxy: Proxy = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        ssl_config = SSLConfig(
            verify=verify, cert=cert, trust_env=trust_env, http2=False
        )
        hard_limit = pool_limits.hard_limit
        soft_limit = pool_limits.soft_limit

        # Our connection pool configuration doesn't quite match up with urllib3's
        # controls, but we can put sensible mappings in place:
        if hard_limit is None:
            block = False
            if soft_limit is None:
                num_pools = 1000
                maxsize = 1000
            else:
                num_pools = int(math.sqrt(soft_limit))
                maxsize = int(math.sqrt(soft_limit))
        else:
            block = True
            num_pools = int(math.sqrt(hard_limit))
            maxsize = int(math.sqrt(hard_limit))

        self.pool = self.init_pool_manager(
            proxy=proxy,
            ssl_context=ssl_config.ssl_context,
            num_pools=num_pools,
            maxsize=maxsize,
            block=block,
        )

    def init_pool_manager(
        self,
        proxy: Optional[Proxy],
        ssl_context: ssl.SSLContext,
        num_pools: int,
        maxsize: int,
        block: bool,
    ) -> Union[urllib3.PoolManager, urllib3.ProxyManager]:
        if proxy is None:
            return urllib3.PoolManager(
                ssl_context=ssl_context,
                num_pools=num_pools,
                maxsize=maxsize,
                block=block,
            )
        else:
            return urllib3.ProxyManager(
                proxy_url=str(proxy.url),
                proxy_headers=dict(proxy.headers),
                ssl_context=ssl_context,
                num_pools=num_pools,
                maxsize=maxsize,
                block=block,
            )

    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, int, bytes],
        headers: List[Tuple[bytes, bytes]] = None,
        stream: httpcore.SyncByteStream = None,
        timeout: Dict[str, Optional[float]] = None,
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.SyncByteStream]:
        headers = [] if headers is None else headers
        stream = ByteStream(b"") if stream is None else stream
        timeout = {} if timeout is None else timeout

        urllib3_timeout = urllib3.util.Timeout(
            connect=timeout.get("connect"), read=timeout.get("read")
        )

        chunked = False
        content_length = 0
        for header_key, header_value in headers:
            header_key = header_key.lower()
            if header_key == b"transfer-encoding":
                chunked = header_value == b"chunked"
            if header_key == b"content-length":
                content_length = int(header_value.decode("ascii"))
        body = stream if chunked or content_length else None

        scheme, host, port, path = url
        default_scheme = {80: b"http", 443: "https"}.get(port)
        if scheme == default_scheme:
            url_str = "%s://%s%s" % (
                scheme.decode("ascii"),
                host.decode("ascii"),
                path.decode("ascii"),
            )
        else:
            url_str = "%s://%s:%d%s" % (
                scheme.decode("ascii"),
                host.decode("ascii"),
                port,
                path.decode("ascii"),
            )

        with as_network_error(MaxRetryError, SSLError, socket.error):
            conn = self.pool.urlopen(
                method=method.decode(),
                url=url_str,
                headers=dict(
                    [
                        (key.decode("ascii"), value.decode("ascii"))
                        for key, value in headers
                    ]
                ),
                body=body,
                redirect=False,
                assert_same_host=False,
                retries=0,
                preload_content=False,
                chunked=chunked,
                timeout=urllib3_timeout,
                pool_timeout=timeout.get("pool"),
            )

        def response_bytes() -> Iterator[bytes]:
            with as_network_error(socket.error):
                for chunk in conn.stream(4096, decode_content=False):
                    yield chunk

        status_code = conn.status
        headers = list(conn.headers.items())
        response_stream = IteratorStream(
            iterator=response_bytes(), close_func=conn.release_conn
        )
        return (b"HTTP/1.1", status_code, conn.reason, headers, response_stream)

    def close(self) -> None:
        self.pool.clear()
