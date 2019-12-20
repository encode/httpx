import asyncio
import json
import os
import threading
import time
import typing

import pytest
import trustme
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    load_pem_private_key,
)
from uvicorn.config import Config
from uvicorn.main import Server

from httpx import URL
from httpx.backends.asyncio import AsyncioBackend
from httpx.backends.base import lookup_backend

ENVIRONMENT_VARIABLES = {
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "SSLKEYLOGFILE",
}


@pytest.fixture(scope="function", autouse=True)
def clean_environ() -> typing.Dict[str, typing.Any]:
    """Keeps os.environ clean for every test without having to mock os.environ"""
    original_environ = os.environ.copy()
    os.environ.clear()
    os.environ.update(
        {
            k: v
            for k, v in original_environ.items()
            if k not in ENVIRONMENT_VARIABLES and k.lower() not in ENVIRONMENT_VARIABLES
        }
    )
    yield
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture(
    params=[
        # pytest uses the marks to set up the specified async environment and run
        # 'async def' test functions. The "auto" backend should then auto-detect
        # the environment it's running in.
        # Passing the backend explicitly, e.g. `backend="asyncio"`,
        # is tested separately.
        pytest.param("auto", marks=pytest.mark.asyncio),
        pytest.param("auto", marks=pytest.mark.trio),
    ]
)
def backend(request):
    return request.param


async def app(scope, receive, send):
    assert scope["type"] == "http"
    if scope["path"].startswith("/slow_response"):
        await slow_response(scope, receive, send)
    elif scope["path"].startswith("/premature_close"):
        await premature_close(scope, receive, send)
    elif scope["path"].startswith("/status"):
        await status_code(scope, receive, send)
    elif scope["path"].startswith("/echo_body"):
        await echo_body(scope, receive, send)
    elif scope["path"].startswith("/echo_headers"):
        await echo_headers(scope, receive, send)
    elif scope["path"].startswith("/redirect_301"):
        await redirect_301(scope, receive, send)
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
    delay_ms_str: str = scope["path"].replace("/slow_response/", "")
    try:
        delay_ms = float(delay_ms_str)
    except ValueError:
        delay_ms = 100
    await asyncio.sleep(delay_ms / 1000.0)
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


async def premature_close(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )


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


async def echo_headers(scope, receive, send):
    body = {}
    for name, value in scope.get("headers", []):
        body[name.capitalize().decode()] = value.decode()

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": json.dumps(body).encode()})


async def redirect_301(scope, receive, send):
    await send(
        {"type": "http.response.start", "status": 301, "headers": [[b"location", b"/"]]}
    )
    await send({"type": "http.response.body"})


SERVER_SCOPE = "session"


@pytest.fixture(scope=SERVER_SCOPE)
def cert_authority():
    return trustme.CA()


@pytest.fixture(scope=SERVER_SCOPE)
def ca_cert_pem_file(cert_authority):
    with cert_authority.cert_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture(scope=SERVER_SCOPE)
def localhost_cert(cert_authority):
    return cert_authority.issue_cert("localhost")


@pytest.fixture(scope=SERVER_SCOPE)
def cert_pem_file(localhost_cert):
    with localhost_cert.cert_chain_pems[0].tempfile() as tmp:
        yield tmp


@pytest.fixture(scope=SERVER_SCOPE)
def cert_private_key_file(localhost_cert):
    with localhost_cert.private_key_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture(scope=SERVER_SCOPE)
def cert_encrypted_private_key_file(localhost_cert):
    # Deserialize the private key and then reserialize with a password
    private_key = load_pem_private_key(
        localhost_cert.private_key_pem.bytes(), password=None, backend=default_backend()
    )
    encrypted_private_key_pem = trustme.Blob(
        private_key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            BestAvailableEncryption(password=b"password"),
        )
    )
    with encrypted_private_key_pem.tempfile() as tmp:
        yield tmp


class TestServer(Server):
    @property
    def url(self) -> URL:
        protocol = "https" if self.config.is_ssl else "http"
        return URL(f"{protocol}://{self.config.host}:{self.config.port}/")

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
    asyncio_backend = AsyncioBackend()
    backend_implementation = lookup_backend(backend)

    async def restart(server):
        await backend_implementation.run_in_threadpool(
            asyncio_backend.run, server.restart
        )

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
def uds_server():
    uds = "test_server.sock"
    config = Config(app=app, lifespan="off", loop="asyncio", uds=uds)
    server = TestServer(config=config)
    yield from serve_in_thread(server)
    os.remove(uds)


@pytest.fixture(scope=SERVER_SCOPE)
def https_server(cert_pem_file, cert_private_key_file):
    config = Config(
        app=app,
        lifespan="off",
        ssl_certfile=cert_pem_file,
        ssl_keyfile=cert_private_key_file,
        host="localhost",
        port=8001,
        loop="asyncio",
    )
    server = TestServer(config=config)
    yield from serve_in_thread(server)


@pytest.fixture(scope=SERVER_SCOPE)
def https_uds_server(cert_pem_file, cert_private_key_file):
    uds = "https_test_server.sock"
    config = Config(
        app=app,
        lifespan="off",
        ssl_certfile=cert_pem_file,
        ssl_keyfile=cert_private_key_file,
        uds=uds,
        loop="asyncio",
    )
    server = TestServer(config=config)
    yield from serve_in_thread(server)
    os.remove(uds)
