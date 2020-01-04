import json
import socket

import h2.connection
import h2.events
import pytest
from h2.settings import SettingCodes

from httpx import AsyncClient, Response, TimeoutException

from .utils import MockHTTP2Backend


async def app(request):
    method = request.method
    path = request.url.path
    body = b"".join([part async for part in request.stream])
    content = json.dumps(
        {"method": method, "path": path, "body": body.decode()}
    ).encode()
    headers = {"Content-Length": str(len(content))}
    return Response(200, headers=headers, content=content, request=request)


@pytest.mark.asyncio
async def test_http2_get_request():
    backend = MockHTTP2Backend(app=app)

    async with AsyncClient(backend=backend, http2=True) as client:
        response = await client.get("http://example.org")

    assert response.status_code == 200
    assert json.loads(response.content) == {"method": "GET", "path": "/", "body": ""}


@pytest.mark.asyncio
async def test_http2_post_request():
    backend = MockHTTP2Backend(app=app)

    async with AsyncClient(backend=backend, http2=True) as client:
        response = await client.post("http://example.org", data=b"<data>")

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": "<data>",
    }


@pytest.mark.asyncio
async def test_http2_large_post_request():
    backend = MockHTTP2Backend(app=app)

    data = b"a" * 100000
    async with AsyncClient(backend=backend, http2=True) as client:
        response = await client.post("http://example.org", data=data)
    assert response.status_code == 200
    assert json.loads(response.content) == {
        "method": "POST",
        "path": "/",
        "body": data.decode(),
    }


@pytest.mark.asyncio
async def test_http2_multiple_requests():
    backend = MockHTTP2Backend(app=app)

    async with AsyncClient(backend=backend, http2=True) as client:
        response_1 = await client.get("http://example.org/1")
        response_2 = await client.get("http://example.org/2")
        response_3 = await client.get("http://example.org/3")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}

    assert response_3.status_code == 200
    assert json.loads(response_3.content) == {"method": "GET", "path": "/3", "body": ""}


@pytest.mark.asyncio
async def test_http2_reconnect():
    """
    If a connection has been dropped between requests, then we should
    be seemlessly reconnected.
    """
    backend = MockHTTP2Backend(app=app)

    async with AsyncClient(backend=backend, http2=True) as client:
        response_1 = await client.get("http://example.org/1")
        backend.server.close_connection = True
        response_2 = await client.get("http://example.org/2")

    assert response_1.status_code == 200
    assert json.loads(response_1.content) == {"method": "GET", "path": "/1", "body": ""}

    assert response_2.status_code == 200
    assert json.loads(response_2.content) == {"method": "GET", "path": "/2", "body": ""}


@pytest.mark.asyncio
async def test_http2_settings_in_handshake():
    backend = MockHTTP2Backend(app=app)

    async with AsyncClient(backend=backend, http2=True) as client:
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


@pytest.mark.usefixtures("async_environment")
async def test_http2_live_request():
    async with AsyncClient(http2=True) as client:
        try:
            resp = await client.get("https://nghttp2.org/httpbin/anything")
        except TimeoutException:  # pragma: nocover
            pytest.xfail(reason="nghttp2.org appears to be unresponsive")
        except socket.gaierror:  # pragma: nocover
            pytest.xfail(reason="You appear to be offline")
        assert resp.status_code == 200
        assert resp.http_version == "HTTP/2"
