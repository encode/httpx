import asyncio
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
        response = await connection.send(request, stream=stream)
        return response

    async def acquire_connection(
        self, url: URL, *, ssl: typing.Union[bool, ssl.SSLContext] = False
    ) -> Connection:
        connection = Connection(timeout=self.timeout)
        await connection.open(url.hostname, url.port, ssl=ssl)
        return connection

    async def get_ssl_context(self, url: URL) -> typing.Union[bool, ssl.SSLContext]:
        if not url.is_secure:
            return False

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
