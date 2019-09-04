import typing

from ..concurrency.base import ConcurrencyBackend, PoolLimits
from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..exceptions import InvalidURL
from ..models import URL, AsyncRequest, AsyncResponse
from .base import AsyncDispatcher
from .connection_pool import ConnectionPool


class RoutingDispatcher(AsyncDispatcher):
    def __init__(
        self, routes: typing.Dict[str, AsyncDispatcher], backend: ConcurrencyBackend
    ):
        self.routes = routes
        self.backend = backend

        # Allow ConnectionPool instances to share their resources
        pools = [
            pool for pool in self.routes.values() if isinstance(pool, ConnectionPool)
        ]
        if pools:
            max_connections = sum(pool.pool_limits.hard_limit for pool in pools)
            self.max_connections = backend.get_semaphore(
                PoolLimits(hard_limit=max_connections)
            )
            for pool in pools:
                pool.max_connections = self.max_connections

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        for route in self.routes_for_url(request.url):
            dispatcher = self.routes.get(route, None)
            if dispatcher:
                return await dispatcher.send(
                    request=request, verify=verify, cert=cert, timeout=timeout
                )

        raise InvalidURL(f"No dispatcher found for {request.url!r}")

    @staticmethod
    def routes_for_url(url: URL) -> typing.Iterable[str]:
        hostname = url.host
        if url.port is not None:
            hostname += f":{url.port}"
        return f"{url.scheme}://{hostname}", f"all://{hostname}", url.scheme, "all"
