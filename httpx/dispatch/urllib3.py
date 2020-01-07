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
        self.pool = urllib3.PoolManager(ssl_context=ssl.ssl_context)

    def send(self, request: Request, timeout: Timeout = None) -> Response:
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
