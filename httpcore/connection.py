import asyncio
import typing

import h2.connection
import h11

from .config import DEFAULT_SSL_CONFIG, DEFAULT_TIMEOUT_CONFIG, SSLConfig, TimeoutConfig
from .exceptions import ConnectTimeout
from .http2 import HTTP2Connection
from .http11 import HTTP11Connection
from .models import Client, Origin, Request, Response


class HTTPConnection(Client):
    def __init__(
        self,
        origin: typing.Union[str, Origin],
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        on_release: typing.Callable = None,
    ):
        self.origin = Origin(origin) if isinstance(origin, str) else origin
        self.ssl = ssl
        self.timeout = timeout
        self.on_release = on_release
        self.h11_connection = None  # type: typing.Optional[HTTP11Connection]
        self.h2_connection = None  # type: typing.Optional[HTTP2Connection]

    async def send(
        self,
        request: Request,
        *,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        if self.h11_connection is None and self.h2_connection is None:
            if ssl is None:
                ssl = self.ssl
            if timeout is None:
                timeout = self.timeout

            reader, writer, protocol = await self.connect(ssl, timeout)
            if protocol == "h2":
                self.h2_connection = HTTP2Connection(
                    reader,
                    writer,
                    origin=self.origin,
                    timeout=self.timeout,
                    on_release=self.on_release,
                )
            else:
                self.h11_connection = HTTP11Connection(
                    reader,
                    writer,
                    origin=self.origin,
                    timeout=self.timeout,
                    on_release=self.on_release,
                )

        if self.h2_connection is not None:
            response = await self.h2_connection.send(request, ssl=ssl, timeout=timeout)
        else:
            assert self.h11_connection is not None
            response = await self.h11_connection.send(request, ssl=ssl, timeout=timeout)

        return response

    async def close(self) -> None:
        if self.h2_connection is not None:
            await self.h2_connection.close()
        else:
            assert self.h11_connection is not None
            await self.h11_connection.close()

    @property
    def is_closed(self) -> bool:
        if self.h2_connection is not None:
            return self.h2_connection.is_closed
        else:
            assert self.h11_connection is not None
            return self.h11_connection.is_closed

    async def connect(
        self, ssl: SSLConfig, timeout: TimeoutConfig
    ) -> typing.Tuple[asyncio.StreamReader, asyncio.StreamWriter, str]:
        hostname = self.origin.hostname
        port = self.origin.port
        ssl_context = await ssl.load_ssl_context() if self.origin.is_ssl else None

        try:
            reader, writer = await asyncio.wait_for(  # type: ignore
                asyncio.open_connection(hostname, port, ssl=ssl_context),
                timeout.connect_timeout,
            )
        except asyncio.TimeoutError:
            raise ConnectTimeout()

        ssl_object = writer.get_extra_info("ssl_object")
        if ssl_object is None:
            protocol = "http/1.1"
        else:
            protocol = ssl_object.selected_alpn_protocol()
        if protocol is None:
            protocol = ssl_object.selected_npn_protocol()

        return (reader, writer, protocol)
