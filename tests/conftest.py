import asyncio
import threading
import time

import pytest
import trustme
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
)
from uvicorn.config import Config
from uvicorn.main import Server

from httpx import AsyncioBackend


@pytest.fixture(params=[pytest.param(AsyncioBackend, marks=pytest.mark.asyncio)])
def backend(request):
    backend_cls = request.param
    return backend_cls()


async def app(scope, receive, send):
    assert scope["type"] == "http"
    if scope["path"] == "/slow_response":
        await slow_response(scope, receive, send)
    elif scope["path"].startswith("/status"):
        await status_code(scope, receive, send)
    elif scope["path"].startswith("/echo_body"):
        await echo_body(scope, receive, send)
    else:
        await hello_world(scope, receive, send)


async def hello_world(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


async def slow_response(scope, receive, send):
    await asyncio.sleep(0.1)
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


async def status_code(scope, receive, send):
    status_code = int(scope["path"].replace("/status/", ""))
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


async def echo_body(scope, receive, send):
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": body})


class CAWithPKEncryption(trustme.CA):
    """Implementation of trustme.CA() that can emit
    private keys that are encrypted with a password.
    """

    @property
    def encrypted_private_key_pem(self):
        return trustme.Blob(
            self._private_key.private_bytes(
                Encoding.PEM,
                PrivateFormat.TraditionalOpenSSL,
                BestAvailableEncryption(password=b"password"),
            )
        )


SERVER_SCOPE = "session"


@pytest.fixture(scope=SERVER_SCOPE)
def example_cert():
    ca = CAWithPKEncryption()
    ca.issue_cert("example.org")
    return ca


@pytest.fixture(scope=SERVER_SCOPE)
def cert_pem_file(example_cert):
    with example_cert.cert_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture(scope=SERVER_SCOPE)
def cert_private_key_file(example_cert):
    with example_cert.private_key_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture(scope=SERVER_SCOPE)
def cert_encrypted_private_key_file(example_cert):
    with example_cert.encrypted_private_key_pem.tempfile() as tmp:
        yield tmp


class TestServer(Server):
    def install_signal_handlers(self) -> None:
        # Disable the default installation of handlers for signals such as SIGTERM,
        # because it can only be done in the main thread.
        pass

    async def serve(self, sockets=None):
        self.restart_requested = asyncio.Event()

        loop = asyncio.get_event_loop()
        tasks = {
            loop.create_task(super().serve(sockets=sockets)),
            loop.create_task(self.watch_restarts()),
        }

        await asyncio.wait(tasks)

    async def restart(self) -> None:
        # Ensure we are in an asyncio environment.
        assert asyncio.get_event_loop() is not None
        # This may be called from a different thread than the one the server is
        # running on. For this reason, we use an event to coordinate with the server
        # instead of calling shutdown()/startup() directly.
        self.restart_requested.set()
        self.started = False
        while not self.started:
            await asyncio.sleep(0.5)

    async def watch_restarts(self):
        while True:
            if self.should_exit:
                return

            try:
                await asyncio.wait_for(self.restart_requested.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            self.restart_requested.clear()
            await self.shutdown()
            await self.startup()


@pytest.fixture
def restart(backend):
    """Restart the running server from an async test function.

    This fixture deals with possible differences between the environment of the
    test function and that of the server.
    """

    async def restart(server):
        await backend.run_in_threadpool(AsyncioBackend().run, server.restart)

    return restart


def serve_in_thread(server: Server):
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        while not server.started:
            time.sleep(1e-3)
        yield server
    finally:
        server.should_exit = True
        thread.join()


@pytest.fixture(scope=SERVER_SCOPE)
def server():
    config = Config(app=app, lifespan="off", loop="asyncio")
    server = TestServer(config=config)
    yield from serve_in_thread(server)


@pytest.fixture(scope=SERVER_SCOPE)
def https_server(cert_pem_file, cert_private_key_file):
    config = Config(
        app=app,
        lifespan="off",
        ssl_certfile=cert_pem_file,
        ssl_keyfile=cert_private_key_file,
        port=8001,
        loop="asyncio",
    )
    server = TestServer(config=config)
    yield from serve_in_thread(server)
