import asyncio

import pytest
import trustme
from uvicorn.config import Config
from uvicorn.main import Server
from cryptography.hazmat.primitives.serialization import (
    PrivateFormat, BestAvailableEncryption
)
from cryptography.hazmat.primitives.serialization import Encoding


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


@pytest.fixture
def cert_and_key_paths():
    ca = trustme.CA()
    ca.issue_cert("example.org")
    with ca.cert_pem.tempfile() as cert_temp_path, ca.private_key_pem.tempfile() as key_temp_path:
        yield cert_temp_path, key_temp_path


class CAWithPKEncryption(trustme.CA):
    """Implementation of trustme.CA() that emits private keys
    that are encrypted with a password.
    """
    @property
    def private_key_pem(self):
        return trustme.Blob(
            self._private_key.private_bytes(
                Encoding.PEM,
                PrivateFormat.TraditionalOpenSSL,
                BestAvailableEncryption(password=b"password")
            )
        )


@pytest.fixture
def cert_and_encrypted_key_paths():
    ca = CAWithPKEncryption()
    ca.issue_cert("example.org")
    with ca.cert_pem.tempfile() as cert_temp_path, ca.private_key_pem.tempfile() as key_temp_path:
        yield cert_temp_path, key_temp_path


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
async def https_server(cert_and_key_paths):
    cert_path, key_path = cert_and_key_paths
    config = Config(
        app=app, lifespan="off", ssl_certfile=cert_path, ssl_keyfile=key_path, port=8001
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
