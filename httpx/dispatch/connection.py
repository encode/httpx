import enum
import ssl
import typing

import h11

from ..concurrency.base import BaseSocketStream, ConcurrencyBackend, lookup_backend
from ..config import CertTypes, SSLConfig, Timeout, VerifyTypes
from ..models import URL, Origin, Request, Response
from ..utils import get_logger
from .base import Dispatcher, OpenConnection
from .http2 import HTTP2Connection
from .http11 import HTTP11Connection

ReleaseCallback = typing.Callable[["HTTPConnection"], typing.Awaitable[None]]

logger = get_logger(__name__)


class ConnectionState(enum.IntEnum):
    PENDING = 0
    IDLE_HTTP_11 = 1
    IDLE_HTTP_2 = 2
    ACTIVE_HTTP_11 = 3
    ACTIVE_HTTP_2 = 4
    ACTIVE_HTTP_2_NO_STREAMS = 5
    CLOSED = 6


class HTTPConnection(Dispatcher):
    def __init__(
        self,
        origin: typing.Union[str, Origin],
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        trust_env: bool = None,
        http2: bool = False,
        backend: typing.Union[str, ConcurrencyBackend] = "auto",
        release_func: typing.Optional[ReleaseCallback] = None,
        uds: typing.Optional[str] = None,
    ):
        self.origin = Origin(origin) if isinstance(origin, str) else origin
        self.ssl = SSLConfig(cert=cert, verify=verify, trust_env=trust_env)
        self.http2 = http2
        self.backend = lookup_backend(backend)
        self.release_func = release_func
        self.uds = uds
        self.connection: typing.Optional[OpenConnection] = None
        self.state = ConnectionState.PENDING

    async def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: Timeout = None,
    ) -> Response:
        timeout = Timeout() if timeout is None else timeout

        if self.state == ConnectionState.PENDING:
            try:
                await self.connect(verify=verify, cert=cert, timeout=timeout)
                assert self.connection is not None
                if self.connection.is_http2:
                    self.state = ConnectionState.ACTIVE_HTTP_2
                else:
                    self.state = ConnectionState.ACTIVE_HTTP_11
            except BaseException as exc:
                self.state = ConnectionState.CLOSED
                raise exc
        elif self.state == ConnectionState.IDLE_HTTP_11:
            self.state = ConnectionState.ACTIVE_HTTP_11
        elif self.state == ConnectionState.IDLE_HTTP_2:
            self.state = ConnectionState.ACTIVE_HTTP_2
        # elif self.state == ConnectionState.ACTIVE_HTTP_2:
        #     pass
        # else:  # ACTIVE_HTTP_11, ACTIVE_HTTP_2_NO_STREAMS, CLOSED
        #     raise NewConnectionRequired()

        assert self.connection is not None
        try:
            return await self.connection.send(request, timeout=timeout)
        except BaseException as exc:
            self.state = ConnectionState.CLOSED
            raise exc from None

    async def connect(
        self, timeout: Timeout, verify: VerifyTypes = None, cert: CertTypes = None,
    ) -> None:
        ssl = self.ssl.with_overrides(verify=verify, cert=cert)

        host = self.origin.host
        port = self.origin.port
        ssl_context = await self.get_ssl_context(ssl)

        if self.uds is None:
            stream = await self.backend.open_tcp_stream(
                host, port, ssl_context, timeout
            )
        else:
            stream = await self.backend.open_uds_stream(
                self.uds, host, ssl_context, timeout
            )

        self.connection = self.new_connection(stream)

    async def tunnel_start_tls(
        self,
        origin: Origin,
        proxy_url: URL,
        timeout: Timeout = None,
        cert: CertTypes = None,
        verify: VerifyTypes = True,
    ) -> None:
        """
        Upgrade this connection to use TLS, assuming it represents a TCP tunnel.
        """
        timeout = Timeout() if timeout is None else timeout

        # First, check that we are in the correct state to start TLS, i.e. we've
        # just agreed to switch protocols with the server via HTTP/1.1.
        assert isinstance(self.connection, HTTP11Connection)
        h11_connection = self.connection
        assert h11_connection is not None
        assert h11_connection.h11_state.our_state == h11.SWITCHED_PROTOCOL

        # Store this information here so that we can transfer
        # it to the new internal connection object after
        # the old one goes to 'SWITCHED_PROTOCOL'.
        # Note that the negotiated 'http_version' may change after the TLS upgrade.
        socket = h11_connection.socket

        if not origin.is_ssl:
            self.connection = self.new_connection(socket)
            return

        # Pull the socket stream off the internal HTTP connection object,
        # and run start_tls().
        ssl_config = SSLConfig(cert=cert, verify=verify)
        ssl_context = await self.get_ssl_context(ssl_config)
        assert ssl_context is not None

        socket = await socket.start_tls(
            hostname=origin.host, ssl_context=ssl_context, timeout=timeout
        )
        self.connection = self.new_connection(socket)

    def new_connection(self, socket: BaseSocketStream) -> OpenConnection:
        http_version = socket.get_http_version()
        if http_version == "HTTP/2":
            return HTTP2Connection(socket, self.backend, on_release=self.release)
        return HTTP11Connection(socket, on_release=self.release)

    async def get_ssl_context(self, ssl: SSLConfig) -> typing.Optional[ssl.SSLContext]:
        if not self.origin.is_ssl:
            return None

        # Run the SSL loading in a threadpool, since it may make disk accesses.
        return await self.backend.run_in_threadpool(ssl.load_ssl_context, self.http2)

    async def release(self) -> None:
        logger.trace("Connection released")
        if self.state == ConnectionState.ACTIVE_HTTP_11:
            self.state = ConnectionState.IDLE_HTTP_11
        elif self.state == ConnectionState.ACTIVE_HTTP_2:
            self.state = ConnectionState.IDLE_HTTP_2
        elif self.state == ConnectionState.ACTIVE_HTTP_2_NO_STREAMS:
            self.state = ConnectionState.CLOSED

        if self.release_func is not None:
            await self.release_func(self)

    def __repr__(self) -> str:
        return f"<Connection [{self.origin!r} {self.state.name}]>"

    async def close(self) -> None:
        logger.trace("close_connection")
        if self.connection is not None:
            await self.connection.close()

    @property
    def is_http2(self) -> bool:
        assert self.connection is not None
        return self.connection.is_http2

    @property
    def is_closed(self) -> bool:
        assert self.connection is not None
        return self.connection.is_closed

    def is_connection_dropped(self) -> bool:
        assert self.connection is not None
        return self.connection.is_connection_dropped()
