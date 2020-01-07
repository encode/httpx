import typing

from ..backends.base import BaseSemaphore, ConcurrencyBackend, lookup_backend
from ..config import (
    DEFAULT_POOL_LIMITS,
    CertTypes,
    PoolLimits,
    SSLConfig,
    Timeout,
    VerifyTypes,
)
from ..exceptions import PoolTimeout
from ..models import Origin, Request, Response
from ..utils import get_logger
from .base import AsyncDispatcher
from .connection import HTTPConnection

CONNECTIONS_DICT = typing.Dict[Origin, typing.List[HTTPConnection]]


logger = get_logger(__name__)


class NullSemaphore(BaseSemaphore):
    async def acquire(self, timeout: float = None) -> None:
        return

    def release(self) -> None:
        return


class ConnectionStore:
    """
    We need to maintain collections of connections in a way that allows us to:

    * Lookup connections by origin.
    * Iterate over connections by insertion time.
    * Return the total number of connections.
    """

    def __init__(self) -> None:
        self.all: typing.Dict[HTTPConnection, float] = {}
        self.by_origin: typing.Dict[Origin, typing.Dict[HTTPConnection, float]] = {}

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


class ConnectionPool(AsyncDispatcher):
    KEEP_ALIVE_EXPIRY = 5.0

    def __init__(
        self,
        *,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        http2: bool = False,
        backend: typing.Union[str, ConcurrencyBackend] = "auto",
        uds: typing.Optional[str] = None,
    ):
        self.ssl = SSLConfig(verify=verify, cert=cert, trust_env=trust_env, http2=http2)
        self.pool_limits = pool_limits
        self.is_closed = False
        self.uds = uds

        self.keepalive_connections = ConnectionStore()
        self.active_connections = ConnectionStore()

        self.backend = lookup_backend(backend)
        self.next_keepalive_check = 0.0

    @property
    def max_connections(self) -> BaseSemaphore:
        # We do this lazily, to make sure backend autodetection always
        # runs within an async context.
        if not hasattr(self, "_max_connections"):
            limit = self.pool_limits.hard_limit
            if limit:
                self._max_connections = self.backend.create_semaphore(
                    limit, exc_class=PoolTimeout
                )
            else:
                self._max_connections = NullSemaphore()

        return self._max_connections

    @property
    def num_connections(self) -> int:
        return len(self.keepalive_connections) + len(self.active_connections)

    async def check_keepalive_expiry(self) -> None:
        now = self.backend.time()
        if now < self.next_keepalive_check:
            return
        self.next_keepalive_check = now + 1.0

        # Iterate through all the keep alive connections.
        # We create a list here to avoid any 'changed during iteration' errors.
        keepalives = list(self.keepalive_connections.all.keys())
        for connection in keepalives:
            if connection.expires_at is not None and now > connection.expires_at:
                self.keepalive_connections.remove(connection)
                self.max_connections.release()
                await connection.close()

    async def send(self, request: Request, timeout: Timeout = None) -> Response:
        await self.check_keepalive_expiry()
        connection = await self.acquire_connection(
            origin=Origin(request.url), timeout=timeout
        )
        try:
            response = await connection.send(request, timeout=timeout)
        except BaseException as exc:
            self.active_connections.remove(connection)
            self.max_connections.release()
            raise exc

        return response

    async def acquire_connection(
        self, origin: Origin, timeout: Timeout = None
    ) -> HTTPConnection:
        logger.trace(f"acquire_connection origin={origin!r}")
        connection = self.pop_connection(origin)

        if connection is None:
            pool_timeout = None if timeout is None else timeout.pool_timeout

            await self.max_connections.acquire(timeout=pool_timeout)
            connection = HTTPConnection(
                origin,
                ssl=self.ssl,
                backend=self.backend,
                release_func=self.release_connection,
                uds=self.uds,
            )
            logger.trace(f"new_connection connection={connection!r}")
        else:
            logger.trace(f"reuse_connection connection={connection!r}")

        self.active_connections.add(connection)

        return connection

    async def release_connection(self, connection: HTTPConnection) -> None:
        logger.trace(f"release_connection connection={connection!r}")
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
            now = self.backend.time()
            connection.expires_at = now + self.KEEP_ALIVE_EXPIRY
            self.active_connections.remove(connection)
            self.keepalive_connections.add(connection)

    async def close(self) -> None:
        self.is_closed = True
        connections = list(self.keepalive_connections)
        self.keepalive_connections.clear()
        for connection in connections:
            self.max_connections.release()
            await connection.close()

    def pop_connection(self, origin: Origin) -> typing.Optional[HTTPConnection]:
        connection = self.active_connections.pop_by_origin(origin, http2_only=True)
        if connection is None:
            connection = self.keepalive_connections.pop_by_origin(origin)

        if connection is not None and connection.is_connection_dropped():
            self.max_connections.release()
            connection = None

        return connection
