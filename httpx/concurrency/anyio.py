import typing

import anyio

from ..config import TimeoutConfig
from ..exceptions import ConnectTimeout, ReadTimeout


class Datagram:
    def __init__(self, data: bytes, address: str, port: int):
        self.data = data
        self.address = address
        self.port = port


class UDPStream:
    def __init__(self, socket: anyio.UDPSocket, timeout: TimeoutConfig):
        self.socket = socket
        self.timeout = timeout

    async def read(
        self, n: int, timeout: TimeoutConfig = None, flag: typing.Any = None
    ) -> Datagram:
        if timeout is None:
            timeout = self.timeout

        read_timeout = (
            timeout.read_timeout if timeout.read_timeout is not None else float("inf")
        )

        while True:
            # Check our flag at the first possible moment, and use a fine
            # grained retry loop if we're not yet in read-timeout mode.
            should_raise = flag is None or flag.raise_on_read_timeout

            if should_raise:
                read_timeout = (
                    timeout.read_timeout
                    if timeout.read_timeout is not None
                    else float("inf")
                )
            else:
                read_timeout = 0.01

            async with anyio.move_on_after(read_timeout):
                data, (address, port) = await self.socket.receive(n)
                return Datagram(data=data, address=address, port=port)

            if should_raise:
                raise ReadTimeout() from None

    async def write(self, data: bytes) -> None:
        await self.socket.send(data)

    async def close(self) -> None:
        await self.socket.close()


class AnyioBackend:
    async def open_udp_stream(
        self, host: str, port: int, timeout: TimeoutConfig
    ) -> UDPStream:
        connect_timeout = (
            timeout.connect_timeout
            if timeout.connect_timeout is not None
            else float("int")
        )

        async with anyio.move_on_after(connect_timeout):
            socket = await anyio.create_udp_socket(target_host=host, target_port=port)
            return UDPStream(socket=socket, timeout=timeout)

        raise ConnectTimeout()
