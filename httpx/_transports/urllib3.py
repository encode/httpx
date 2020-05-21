import math
import socket
import ssl
from typing import Dict, Iterator, List, Optional, Tuple, Union

import httpcore

from .._config import DEFAULT_POOL_LIMITS, PoolLimits, Proxy, SSLConfig
from .._content_streams import ByteStream, IteratorStream
from .._types import CertTypes, VerifyTypes
from .._utils import as_network_error, warn_deprecated

try:
    import urllib3
    from urllib3.exceptions import MaxRetryError, SSLError
except ImportError:  # pragma: nocover
    urllib3 = None


class URLLib3Transport(httpcore.SyncHTTPTransport):
    def __init__(
        self,
        *,
        proxy: Proxy = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        pool_block: bool = False,
    ):
        assert (
            urllib3 is not None
        ), "urllib3 must be installed separately in order to use URLLib3Transport"

        ssl_config = SSLConfig(
            verify=verify, cert=cert, trust_env=trust_env, http2=False
        )
        max_connections = pool_limits.max_connections
        max_keepalive = pool_limits.max_keepalive

        # Our connection pool configuration doesn't quite match up with urllib3's
        # controls, but we can put sensible mappings in place:
        if max_connections is None:
            block = False
            if max_keepalive is None:
                num_pools = 1000
                maxsize = 1000
            else:
                num_pools = int(math.sqrt(max_keepalive))
                maxsize = int(math.sqrt(max_keepalive))
        else:
            block = True
            num_pools = int(math.sqrt(max_connections))
            maxsize = int(math.sqrt(max_connections))

        self.pool = self.init_pool_manager(
            proxy=proxy,
            ssl_context=ssl_config.ssl_context,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            pool_block=pool_block,
        )

    def init_pool_manager(
        self,
        proxy: Optional[Proxy],
        ssl_context: ssl.SSLContext,
        pool_connections: int,
        pool_maxsize: int,
        pool_block: bool,
    ) -> Union[urllib3.PoolManager, urllib3.ProxyManager]:
        if proxy is None:
            return urllib3.PoolManager(
                ssl_context=ssl_context,
                num_pools=pool_connections,
                maxsize=pool_maxsize,
                block=pool_block,
            )
        else:
            return urllib3.ProxyManager(
                proxy_url=str(proxy.url),
                proxy_headers=dict(proxy.headers),
                ssl_context=ssl_context,
                num_pools=pool_connections,
                maxsize=pool_maxsize,
                block=pool_block,
            )

    def request(
        self,
        method: bytes,
        url: Tuple[bytes, bytes, Optional[int], bytes],
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
        default_port = {b"http": 80, "https": 443}.get(scheme)
        if port is None or port == default_port:
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


class URLLib3Dispatch(URLLib3Transport):
    def __init__(
        self,
        *,
        proxy: Proxy = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        warn_deprecated("URLLib3Dispatch is deprecated, please use URLLib3Transport")
        super().__init__(
            proxy=proxy,
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            pool_limits=pool_limits,
        )
