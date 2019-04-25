import typing

from .config import (
    DEFAULT_CA_BUNDLE_PATH,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from .connection import HTTPConnection
from .exceptions import PoolTimeout
from .models import Client, Origin, Request, Response
from .streams import PoolSemaphore


class ConnectionPool(Client):
    def __init__(
        self,
        *,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        self.ssl = ssl
        self.timeout = timeout
        self.limits = limits
        self.is_closed = False
        self.num_active_connections = 0
        self.num_keepalive_connections = 0
        self._keepalive_connections = (
            {}
        )  # type: typing.Dict[Origin, typing.List[HTTPConnection]]
        self._max_connections = PoolSemaphore(limits, timeout)

    async def send(
        self,
        request: Request,
        *,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        connection = await self.acquire_connection(request.url.origin, timeout=timeout)
        response = await connection.send(request, ssl=ssl, timeout=timeout)
        return response

    @property
    def num_connections(self) -> int:
        return self.num_active_connections + self.num_keepalive_connections

    async def acquire_connection(
        self, origin: Origin, timeout: typing.Optional[TimeoutConfig] = None
    ) -> HTTPConnection:
        try:
            connection = self._keepalive_connections[origin].pop()
            if not self._keepalive_connections[origin]:
                del self._keepalive_connections[origin]
            self.num_keepalive_connections -= 1
            self.num_active_connections += 1

        except (KeyError, IndexError):
            await self._max_connections.acquire(timeout)
            connection = HTTPConnection(
                origin,
                ssl=self.ssl,
                timeout=self.timeout,
                on_release=self.release_connection,
            )
            self.num_active_connections += 1

        return connection

    async def release_connection(self, connection: HTTPConnection) -> None:
        if connection.is_closed:
            self._max_connections.release()
            self.num_active_connections -= 1
        elif (
            self.limits.soft_limit is not None
            and self.num_connections > self.limits.soft_limit
        ):
            self._max_connections.release()
            self.num_active_connections -= 1
            await connection.close()
        else:
            self.num_active_connections -= 1
            self.num_keepalive_connections += 1
            try:
                self._keepalive_connections[connection.origin].append(connection)
            except KeyError:
                self._keepalive_connections[connection.origin] = [connection]

    async def close(self) -> None:
        self.is_closed = True
        all_connections = []
        for connections in self._keepalive_connections.values():
            all_connections.extend(list(connections))
        self._keepalive_connections.clear()
        for connection in all_connections:
            await connection.close()
