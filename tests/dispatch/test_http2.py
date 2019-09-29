import asyncio
import json
import sys
import threading

import h2.connection
import h2.events
import pytest
from h2.settings import SettingCodes
from hypercorn.asyncio import serve
from hypercorn.config import Config

from httpx import AsyncClient, Client, Response

from .utils import MockHTTP2Backend


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope["type"] == "http":
        assert scope["http_version"] == "2"

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        content = json.dumps(
            {"method": scope["method"], "path": scope["path"], "body": body.decode()}
        ).encode()
        headers = [(b"content-length", b"%d" % len(content))]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": content, "more_body": False})
    else:
        raise Exception()


@pytest.fixture(name="h2_server", scope="module")
def _h2_server(cert_pem_file, cert_private_key_file):
    bind = "0.0.0.0:8543"
    shutdown_event = threading.Event()

    async def _shutdown_trigger():
        while not shutdown_event.is_set():
            await asyncio.sleep(0.1)

    def _run():
        config = Config()
        config.bind = bind
        config.certfile = cert_pem_file
        config.keyfile = cert_private_key_file
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(serve(app, config, shutdown_trigger=_shutdown_trigger))

    thread = threading.Thread(target=_run)
    thread.start()
    import time

    time.sleep(0.5)
    yield f"https://{bind}"
    shutdown_event.set()
    thread.join()


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
def test_http2_get_request(h2_server):
    with Client(http_versions=["HTTP/2"], verify=False) as client:
        response = client.get(h2_server)

    assert response.status_code == 200
    assert json.loads(response.content) == {"method": "GET", "path": "/", "body": ""}


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
async def test_async_http2_get_request(backend, h2_server):
    async with AsyncClient(
        backend=backend, http_versions=["HTTP/2"], verify=False
    ) as client:
        response = await client.get(h2_server)

    assert response.status_code == 200
    assert json.loads(response.content) == {"method": "GET", "path": "/", "body": ""}


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
def test_http2_post_request(h2_server):
    with Client(http_versions=["HTTP/2"], verify=False) as client:
        response = client.post(h2_server, data=b"<data>")

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": "<data>",
    }


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
async def test_async_http2_post_request(backend, h2_server):
    async with AsyncClient(
        backend=backend, http_versions=["HTTP/2"], verify=False
    ) as client:
        response = await client.post(h2_server, data=b"<data>")

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": "<data>",
    }


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
def test_http2_large_post_request(h2_server):
    data = b"a" * 100000
    with Client(http_versions=["HTTP/2"], verify=False) as client:
        response = client.post(h2_server, data=data)
    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": data.decode(),
    }


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
async def test_async_http2_large_post_request(backend, h2_server):
    data = b"a" * 100000
    async with AsyncClient(
        backend=backend, http_versions=["HTTP/2"], verify=False
    ) as client:
        response = await client.post(h2_server, data=data)
    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": data.decode(),
    }


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
def test_http2_multiple_requests(h2_server):
    with Client(http_versions=["HTTP/2"], verify=False) as client:
        response_1 = client.get(f"{h2_server}/1")
        response_2 = client.get(f"{h2_server}/2")
        response_3 = client.get(f"{h2_server}/3")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}

    assert response_3.status_code == 200
    assert json.loads(response_3.content) == {"method": "GET", "path": "/3", "body": ""}


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Hypercorn requires python3.7 or higher"
)
async def test_async_http2_multiple_requests(backend, h2_server):
    async with AsyncClient(
        backend=backend, http_versions=["HTTP/2"], verify=False
    ) as client:
        response_1 = await client.get(f"{h2_server}/1")
        response_2 = await client.get(f"{h2_server}/2")
        response_3 = await client.get(f"{h2_server}/3")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}

    assert response_3.status_code == 200
    assert json.loads(response_3.content) == {"method": "GET", "path": "/3", "body": ""}


def mock_app(request):
    content = json.dumps(
        {
            "method": request.method,
            "path": request.url.path,
            "body": request.content.decode(),
        }
    ).encode()
    headers = {"Content-Length": str(len(content))}
    return Response(200, headers=headers, content=content)


def test_http2_reconnect():
    """
    If a connection has been dropped between requests, then we should
    be seemlessly reconnected.
    """
    backend = MockHTTP2Backend(app=mock_app)

    with Client(backend=backend) as client:
        response_1 = client.get("http://example.org/1")
        response_2 = client.get("http://example.org/2")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}


async def test_async_http2_reconnect(backend):
    """
    If a connection has been dropped between requests, then we should
    be seemlessly reconnected.
    """
    backend = MockHTTP2Backend(app=mock_app, backend=backend)

    async with AsyncClient(backend=backend) as client:
        response_1 = await client.get("http://example.org/1")
        backend.server.close_connection = True
        response_2 = await client.get("http://example.org/2")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}


async def test_http2_settings_in_handshake(backend):
    backend = MockHTTP2Backend(app=mock_app, backend=backend)

    async with AsyncClient(backend=backend) as client:
        await client.get("http://example.org")

    h2_conn = backend.server.conn

    assert isinstance(h2_conn, h2.connection.H2Connection)
    expected_settings = {
        SettingCodes.HEADER_TABLE_SIZE: 4096,
        SettingCodes.ENABLE_PUSH: 0,
        SettingCodes.MAX_CONCURRENT_STREAMS: 100,
        SettingCodes.INITIAL_WINDOW_SIZE: 65535,
        SettingCodes.MAX_FRAME_SIZE: 16384,
        SettingCodes.MAX_HEADER_LIST_SIZE: 65536,
        # This one's here because h2 helpfully populates remote_settings
        # with default values even if the peer doesn't send the setting.
        SettingCodes.ENABLE_CONNECT_PROTOCOL: 0,
    }
    assert dict(h2_conn.remote_settings) == expected_settings

    # We don't expect the ENABLE_CONNECT_PROTOCOL to be in the handshake
    expected_settings.pop(SettingCodes.ENABLE_CONNECT_PROTOCOL)

    assert len(backend.server.settings_changed) == 1
    settings = backend.server.settings_changed[0]

    assert isinstance(settings, h2.events.RemoteSettingsChanged)
    assert len(settings.changed_settings) == len(expected_settings)
    for setting_code, changed_setting in settings.changed_settings.items():
        assert isinstance(changed_setting, h2.settings.ChangedSetting)
        assert changed_setting.new_value == expected_settings[setting_code]


async def test_http2_live_request(backend):
    async with AsyncClient(backend=backend) as client:
        resp = await client.get("https://nghttp2.org/httpbin/anything")

        assert resp.status_code == 200
        assert resp.http_version == "HTTP/2"
