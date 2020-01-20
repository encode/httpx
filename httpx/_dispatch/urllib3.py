import math
import socket
import ssl
import typing

import urllib3
from urllib3.exceptions import MaxRetryError, SSLError

from .._config import (
    DEFAULT_POOL_LIMITS,
    CertTypes,
    PoolLimits,
    Proxy,
    SSLConfig,
    Timeout,
    VerifyTypes,
)
from .._content_streams import IteratorStream
from .._models import Request, Response
from .._utils import as_network_error
from .base import SyncDispatcher


class URLLib3Dispatcher(SyncDispatcher):
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
        proxy: typing.Optional[Proxy],
        ssl_context: ssl.SSLContext,
        num_pools: int,
        maxsize: int,
        block: bool,
    ) -> typing.Union[urllib3.PoolManager, urllib3.ProxyManager]:
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

    def send(self, request: Request, timeout: Timeout = None) -> Response:
        timeout = Timeout() if timeout is None else timeout
        urllib3_timeout = urllib3.util.Timeout(
            connect=timeout.connect_timeout, read=timeout.read_timeout
        )
        chunked = request.headers.get("Transfer-Encoding") == "chunked"
        content_length = int(request.headers.get("Content-Length", "0"))
        body = request.stream if chunked or content_length else None

        with as_network_error(MaxRetryError, SSLError, socket.error):
            conn = self.pool.urlopen(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                body=body,
                redirect=False,
                assert_same_host=False,
                retries=0,
                preload_content=False,
                chunked=chunked,
                timeout=urllib3_timeout,
                pool_timeout=timeout.pool_timeout,
            )

        def response_bytes() -> typing.Iterator[bytes]:
            with as_network_error(socket.error):
                for chunk in conn.stream(4096, decode_content=False):
                    yield chunk

        return Response(
            status_code=conn.status,
            http_version="HTTP/1.1",
            headers=list(conn.headers.items()),
            stream=IteratorStream(
                iterator=response_bytes(), close_func=conn.release_conn
            ),
            request=request,
        )

    def close(self) -> None:
        self.pool.clear()
