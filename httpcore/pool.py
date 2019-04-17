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

ConnectionKey = typing.Tuple[str, str, int]  # (scheme, host, port)


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
        self._connections = (
            {}
        )  # type: typing.Dict[ConnectionKey, typing.List[Connection]]
        self._connection_semaphore = ConnectionSemaphore(
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
    ) -> Response:
        parsed_url = URL(url)
        request = Request(method, parsed_url, headers=headers, body=body)
        ssl_context = await self.get_ssl_context(parsed_url)
        connection = await self.acquire_connection(parsed_url, ssl=ssl_context)
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
        self, url: URL, *, ssl: typing.Optional[ssl.SSLContext] = None
    ) -> Connection:
        key = (url.scheme, url.hostname, url.port)
        try:
            connection = self._connections[key].pop()
            if not self._connections[key]:
                del self._connections[key]
            self.num_keepalive_connections -= 1
            self.num_active_connections += 1

        except (KeyError, IndexError):
            await self._connection_semaphore.acquire()
            release = functools.partial(self.release_connection, key=key)
            connection = Connection(timeout=self.timeout, on_release=release)
            self.num_active_connections += 1
            await connection.open(url.hostname, url.port, ssl=ssl)

        return connection

    async def release_connection(
        self, connection: Connection, key: ConnectionKey
    ) -> None:
        if connection.is_closed:
            self._connection_semaphore.release()
            self.num_active_connections -= 1
        elif (
            self.limits.soft_limit is not None
            and self.num_connections > self.limits.soft_limit
        ):
            self._connection_semaphore.release()
            self.num_active_connections -= 1
            connection.close()
        else:
            self.num_active_connections -= 1
            self.num_keepalive_connections += 1
            try:
                self._connections[key].append(connection)
            except KeyError:
                self._connections[key] = [connection]

    async def get_ssl_context(self, url: URL) -> typing.Optional[ssl.SSLContext]:
        if not url.is_secure:
            return None

        if not hasattr(self, "ssl_context"):
            if not self.ssl_config.verify:
                self.ssl_context = self.get_ssl_context_no_verify()
            else:
                # Run the SSL loading in a threadpool, since it makes disk accesses.
                loop = asyncio.get_event_loop()
                self.ssl_context = await loop.run_in_executor(
                    None, self.get_ssl_context_verify
                )

        return self.ssl_context

    def get_ssl_context_no_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_COMPRESSION
        context.set_default_verify_paths()
        return context

    def get_ssl_context_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for verified connections.
        """
        cert = self.ssl_config.cert
        verify = self.ssl_config.verify

        if isinstance(verify, bool):
            ca_bundle_path = DEFAULT_CA_BUNDLE_PATH
        elif os.path.exists(verify):
            ca_bundle_path = verify
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(verify)
            )

        context = ssl.create_default_context()
        if os.path.isfile(ca_bundle_path):
            context.load_verify_locations(cafile=ca_bundle_path)
        elif os.path.isdir(ca_bundle_path):
            context.load_verify_locations(capath=ca_bundle_path)

        if cert is not None:
            if isinstance(cert, str):
                context.load_cert_chain(certfile=cert)
            else:
                context.load_cert_chain(certfile=cert[0], keyfile=cert[1])

        return context

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
