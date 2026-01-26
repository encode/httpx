import typing

import httpcore
import pytest

import httpx


def test_network_backend():
    class Backend(httpcore.NetworkBackend):
        def connect_tcp(
            self,
            host: str,
            port: int,
            timeout: typing.Optional[float] = None,
            local_address: typing.Optional[str] = None,
            socket_options: typing.Optional[
                typing.Iterable[httpcore.SOCKET_OPTION]
            ] = None,
        ) -> httpcore.NetworkStream:
            return Stream()

    class Stream(httpcore.NetworkStream):
        body = b"\r\n".join(
            [
                b"HTTP/1.1 200 OK",
                b"",
                b"From Backend!",
            ]
        )

        def read(self, max_bytes: int, timeout: typing.Optional[float] = None) -> bytes:
            body = self.body
            if body:
                self.body = b""
            return body

        def write(self, buffer: bytes, timeout: typing.Optional[float] = None) -> None:
            pass

        def close(self) -> None:
            pass

    backend = Backend()
    transport = httpx.HTTPTransport(network_backend=backend)
    with httpx.Client(transport=transport) as client:
        response = client.get("http://www.example.org")
    assert response.status_code == 200
    assert response.text == "From Backend!"


@pytest.mark.anyio
async def test_async_network_backend():
    class AsyncBackend(httpcore.AsyncNetworkBackend):
        async def connect_tcp(
            self,
            host: str,
            port: int,
            timeout: typing.Optional[float] = None,
            local_address: typing.Optional[str] = None,
            socket_options: typing.Optional[
                typing.Iterable[httpcore.SOCKET_OPTION]
            ] = None,
        ) -> httpcore.AsyncNetworkStream:
            return AsyncStream()

    class AsyncStream(httpcore.AsyncNetworkStream):
        body = b"\r\n".join(
            [
                b"HTTP/1.1 200 OK",
                b"",
                b"From Async Backend!",
            ]
        )

        async def read(
            self, max_bytes: int, timeout: typing.Optional[float] = None
        ) -> bytes:
            body = self.body
            if body:
                self.body = b""
            return body

        async def write(
            self, buffer: bytes, timeout: typing.Optional[float] = None
        ) -> None:
            pass

        async def aclose(self) -> None:
            pass

    backend = AsyncBackend()
    transport = httpx.AsyncHTTPTransport(network_backend=backend)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org")
    assert response.status_code == 200
    assert response.text == "From Async Backend!"
