import typing

from ..concurrency import AsyncioBackend
from ..config import (
    DEFAULT_CA_BUNDLE_PATH,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from ..decoders import ACCEPT_ENCODING
from ..exceptions import PoolTimeout
from ..interfaces import ConcurrencyBackend, Dispatcher
from ..models import Origin, Request, Response
from .connection import HTTPConnection

CONNECTIONS_DICT = typing.Dict[Origin, typing.List[HTTPConnection]]


class ConnectionStore:
    """
    We need to maintain collections of connections in a way that allows us to:

    * Lookup connections by origin.
    * Iterate over connections by insertion time.
    * Return the total number of connections.
    """

    def __init__(self) -> None:
        self.all = {}  # type: typing.Dict[HTTPConnection, float]
        self.by_origin = (
            {}
        )  # type: typing.Dict[Origin, typing.Dict[HTTPConnection, float]]

    def pop_by_origin(
        self, origin: Origin, http2_only: bool = False
    ) -> typing.Optional[HTTPConnection]:
        try:
            connections = self.by_origin[origin]
        except KeyError:
            return None

        connection = next(reversed(list(connections.keys())))
        if http2_only and not connection.is_http2:
            return None

        del connections[connection]
        if not connections:
            del self.by_origin[origin]
        del self.all[connection]

        return connection

    def add(self, connection: HTTPConnection) -> None:
        self.all[connection] = 0.0
        try:
            self.by_origin[connection.origin][connection] = 0.0
        except KeyError:
            self.by_origin[connection.origin] = {connection: 0.0}

    def remove(self, connection: HTTPConnection) -> None:
        del self.all[connection]
        del self.by_origin[connection.origin][connection]
        if not self.by_origin[connection.origin]:
            del self.by_origin[connection.origin]

    def clear(self) -> None:
        self.all.clear()
        self.by_origin.clear()

    def __iter__(self) -> typing.Iterator[HTTPConnection]:
        return iter(self.all.keys())

    def __len__(self) -> int:
        return len(self.all)


class ConnectionPool(Dispatcher):
    def __init__(
        self,
        *,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        backend: ConcurrencyBackend = None,
    ):
        self.ssl = ssl
        self.timeout = timeout
        self.pool_limits = pool_limits
        self.is_closed = False

        self.keepalive_connections = ConnectionStore()
        self.active_connections = ConnectionStore()

        self.backend = AsyncioBackend() if backend is None else backend
        self.max_connections = self.backend.get_semaphore(pool_limits)

    @property
    def num_connections(self) -> int:
        return len(self.keepalive_connections) + len(self.active_connections)

    async def send(
        self,
        request: Request,
        stream: bool = False,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> Response:
        connection = await self.acquire_connection(request.url.origin)
        try:
            response = await connection.send(
                request, stream=stream, ssl=ssl, timeout=timeout
            )
        except BaseException as exc:
            self.active_connections.remove(connection)
            self.max_connections.release()
            raise exc
        return response

    async def acquire_connection(self, origin: Origin) -> HTTPConnection:
        connection = self.active_connections.pop_by_origin(origin, http2_only=True)
        if connection is None:
            connection = self.keepalive_connections.pop_by_origin(origin)

        if connection is None:
            await self.max_connections.acquire()
            connection = HTTPConnection(
                origin,
                ssl=self.ssl,
                timeout=self.timeout,
                backend=self.backend,
                release_func=self.release_connection,
            )

        self.active_connections.add(connection)

        return connection

    async def release_connection(self, connection: HTTPConnection) -> None:
        if connection.is_closed:
            self.active_connections.remove(connection)
            self.max_connections.release()
        elif (
            self.pool_limits.soft_limit is not None
            and self.num_connections > self.pool_limits.soft_limit
        ):
            self.active_connections.remove(connection)
            self.max_connections.release()
            await connection.close()
        else:
            self.active_connections.remove(connection)
            self.keepalive_connections.add(connection)

    async def close(self) -> None:
        self.is_closed = True
        connections = list(self.keepalive_connections)
        self.keepalive_connections.clear()
        for connection in connections:
            await connection.close()
