import math
import typing

import urllib3

from ..config import (
    DEFAULT_POOL_LIMITS,
    CertTypes,
    PoolLimits,
    SSLConfig,
    Timeout,
    VerifyTypes,
)
from ..content_streams import IteratorStream
from ..models import Request, Response
from .base import SyncDispatcher


class URLLib3Dispatcher(SyncDispatcher):
    def __init__(
        self,
        *,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        ssl = SSLConfig(verify=verify, cert=cert, trust_env=trust_env, http2=False)
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

        self.pool = urllib3.PoolManager(
            ssl_context=ssl.ssl_context,
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

        conn = self.pool.urlopen(
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            body=request.stream,
            redirect=False,
            assert_same_host=False,
            retries=0,
            preload_content=False,
            chunked=chunked,
            timeout=urllib3_timeout,
            pool_timeout=timeout.pool_timeout,
        )

        def response_bytes() -> typing.Iterator[bytes]:
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
