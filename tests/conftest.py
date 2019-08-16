import asyncio
import functools
import inspect
import threading

import pytest
import trustme
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
)
from uvicorn.config import Config
from uvicorn.main import Server

from httpx.concurrency import AsyncioBackend

try:
    from httpx.contrib.trio import TrioBackend
except ImportError:
    TrioBackend = None  # type: ignore


# All backends should cause tests to be marked (and run under) asyncio,
# because that is the only I/O implementation uvicorn can run on.
MARK_ASYNC = pytest.mark.asyncio


@pytest.fixture(
    params=[
        pytest.param(AsyncioBackend, marks=MARK_ASYNC),
        pytest.param(TrioBackend, marks=MARK_ASYNC),
    ]
)
def backend(request):
    backend_cls = request.param
    if backend_cls is None:
        pytest.skip()
    return backend_cls()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    """
    Run test functions parametrized by the concurrency `backend` in the asyncio
    threadpool instead of a normal function call.

    We do this to prevent the backend-specific event loop from clashing with asyncio.
    """
    if "backend" in pyfuncitem.fixturenames:
        func = pyfuncitem.obj

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapped(backend, *args, **kwargs):
                asyncio_backend = AsyncioBackend()
                await asyncio_backend.run_in_threadpool(
                    backend.run, func, backend, *args, **kwargs
                )

        else:

            @functools.wraps(func)
            async def wrapped(backend, *args, **kwargs):
                asyncio_backend = AsyncioBackend()
                await asyncio_backend.run_in_threadpool(func, backend, *args, **kwargs)

        pyfuncitem.obj = wrapped

    yield


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


@pytest.fixture
def example_cert():
    ca = CAWithPKEncryption()
    ca.issue_cert("example.org")
    return ca


@pytest.fixture
def cert_pem_file(example_cert):
    with example_cert.cert_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture
def cert_private_key_file(example_cert):
    with example_cert.private_key_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture
def cert_encrypted_private_key_file(example_cert):
    with example_cert.encrypted_private_key_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture
async def server():
    config = Config(app=app, lifespan="off")
    server = Server(config=config)
    task = asyncio.ensure_future(server.serve())
    try:
        while not server.started:
            await asyncio.sleep(0.0001)
        yield server
    finally:
        server.should_exit = True
        await task


@pytest.fixture
async def https_server(cert_pem_file, cert_private_key_file):
    config = Config(
        app=app,
        lifespan="off",
        ssl_certfile=cert_pem_file,
        ssl_keyfile=cert_private_key_file,
        port=8001,
    )
    server = Server(config=config)
    task = asyncio.ensure_future(server.serve())
    try:
        while not server.started:
            await asyncio.sleep(0.0001)
        yield server
    finally:
        server.should_exit = True
        await task
