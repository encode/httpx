import asyncio
import functools
import os
import ssl
import typing
from types import TracebackType

from .config import (
    DEFAULT_CA_BUNDLE_PATH,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from .connections import Connection
from .datastructures import URL, Request, Response
from .exceptions import PoolTimeout

ConnectionKey = typing.Tuple[str, str, int, SSLConfig, TimeoutConfig]


class ConnectionSemaphore:
    def __init__(self, max_connections: int = None):
        if max_connections is not None:
            self.semaphore = asyncio.BoundedSemaphore(value=max_connections)

    async def acquire(self) -> None:
        if hasattr(self, "semaphore"):
            await self.semaphore.acquire()

    def release(self) -> None:
        if hasattr(self, "semaphore"):
            self.semaphore.release()


class ConnectionPool:
    def __init__(
        self,
        *,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        self.ssl_config = ssl
        self.timeout = timeout
        self.limits = limits
        self.is_closed = False
        self.num_active_connections = 0
        self.num_keepalive_connections = 0
        self._keepalive_connections = (
            {}
        )  # type: typing.Dict[ConnectionKey, typing.List[Connection]]
        self._max_connections = ConnectionSemaphore(
            max_connections=self.limits.hard_limit
        )

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: typing.Sequence[typing.Tuple[bytes, bytes]] = (),
        body: typing.Union[bytes, typing.AsyncIterator[bytes]] = b"",
        stream: bool = False,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        if ssl is None:
            ssl = self.ssl_config
        if timeout is None:
            timeout = self.timeout

        parsed_url = URL(url)
        request = Request(method, parsed_url, headers=headers, body=body)
        connection = await self.acquire_connection(parsed_url, ssl=ssl, timeout=timeout)
        response = await connection.send(request)
        if not stream:
            try:
                await response.read()
            finally:
                await response.close()
        return response

    @property
    def num_connections(self) -> int:
        return self.num_active_connections + self.num_keepalive_connections

    async def acquire_connection(
        self, url: URL, ssl: SSLConfig, timeout: TimeoutConfig
    ) -> Connection:
        key = (url.scheme, url.hostname, url.port, ssl, timeout)
        try:
            connection = self._keepalive_connections[key].pop()
            if not self._keepalive_connections[key]:
                del self._keepalive_connections[key]
            self.num_keepalive_connections -= 1
            self.num_active_connections += 1

        except (KeyError, IndexError):
            if url.is_secure:
                ssl_context = await ssl.load_ssl_context()
            else:
                ssl_context = None

            try:
                await asyncio.wait_for(
                    self._max_connections.acquire(), timeout.pool_timeout
                )
            except asyncio.TimeoutError:
                raise PoolTimeout()
            release = functools.partial(self.release_connection, key=key)
            connection = Connection(timeout=timeout, on_release=release)
            self.num_active_connections += 1
            await connection.open(url.hostname, url.port, ssl=ssl_context)

        return connection

    async def release_connection(
        self, connection: Connection, key: ConnectionKey
    ) -> None:
        if connection.is_closed:
            self._max_connections.release()
            self.num_active_connections -= 1
        elif (
            self.limits.soft_limit is not None
            and self.num_connections > self.limits.soft_limit
        ):
            self._max_connections.release()
            self.num_active_connections -= 1
            connection.close()
        else:
            self.num_active_connections -= 1
            self.num_keepalive_connections += 1
            try:
                self._keepalive_connections[key].append(connection)
            except KeyError:
                self._keepalive_connections[key] = [connection]

    async def close(self) -> None:
        self.is_closed = True

    async def __aenter__(self) -> "ConnectionPool":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()
