import pytest

import httpx


def app(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/redirect":
        return httpx.Response(303, headers={"server": "testserver", "location": "/"})
    elif request.url.path.startswith("/status/"):
        status_code = int(request.url.path[-3:])
        return httpx.Response(status_code, headers={"server": "testserver"})

    return httpx.Response(200, headers={"server": "testserver"})


def test_event_hooks():
    events = []

    def on_request(request):
        events.append({"event": "request", "headers": dict(request.headers)})

    def on_response(response):
        events.append({"event": "response", "headers": dict(response.headers)})

    event_hooks = {"request": [on_request], "response": [on_response]}

    with httpx.Client(
        event_hooks=event_hooks, transport=httpx.MockTransport(app)
    ) as http:
        http.get("http://127.0.0.1:8000/", auth=("username", "password"))

    assert events == [
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {"server": "testserver"},
        },
    ]


def test_event_hooks_raising_exception(server):
    def raise_on_4xx_5xx(response):
        response.raise_for_status()

    event_hooks = {"response": [raise_on_4xx_5xx]}

    with httpx.Client(
        event_hooks=event_hooks, transport=httpx.MockTransport(app)
    ) as http:
        try:
            http.get("http://127.0.0.1:8000/status/400")
        except httpx.HTTPStatusError as exc:
            assert exc.response.is_closed


@pytest.mark.anyio
async def test_async_event_hooks():
    events = []

    async def on_request(request):
        events.append({"event": "request", "headers": dict(request.headers)})

    async def on_response(response):
        events.append({"event": "response", "headers": dict(response.headers)})

    event_hooks = {"request": [on_request], "response": [on_response]}

    async with httpx.AsyncClient(
        event_hooks=event_hooks, transport=httpx.MockTransport(app)
    ) as http:
        await http.get("http://127.0.0.1:8000/", auth=("username", "password"))

    assert events == [
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {"server": "testserver"},
        },
    ]


@pytest.mark.anyio
async def test_async_event_hooks_raising_exception():
    async def raise_on_4xx_5xx(response):
        response.raise_for_status()

    event_hooks = {"response": [raise_on_4xx_5xx]}

    async with httpx.AsyncClient(
        event_hooks=event_hooks, transport=httpx.MockTransport(app)
    ) as http:
        try:
            await http.get("http://127.0.0.1:8000/status/400")
        except httpx.HTTPStatusError as exc:
            assert exc.response.is_closed


def test_event_hooks_with_redirect():
    """
    A redirect request should trigger additional 'request' and 'response' event hooks.
    """

    events = []

    def on_request(request):
        events.append({"event": "request", "headers": dict(request.headers)})

    def on_response(response):
        events.append({"event": "response", "headers": dict(response.headers)})

    event_hooks = {"request": [on_request], "response": [on_response]}

    with httpx.Client(
        event_hooks=event_hooks,
        transport=httpx.MockTransport(app),
        follow_redirects=True,
    ) as http:
        http.get("http://127.0.0.1:8000/redirect", auth=("username", "password"))

    assert events == [
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {"location": "/", "server": "testserver"},
        },
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {"server": "testserver"},
        },
    ]


@pytest.mark.anyio
async def test_async_event_hooks_with_redirect():
    """
    A redirect request should trigger additional 'request' and 'response' event hooks.
    """

    events = []

    async def on_request(request):
        events.append({"event": "request", "headers": dict(request.headers)})

    async def on_response(response):
        events.append({"event": "response", "headers": dict(response.headers)})

    event_hooks = {"request": [on_request], "response": [on_response]}

    async with httpx.AsyncClient(
        event_hooks=event_hooks,
        transport=httpx.MockTransport(app),
        follow_redirects=True,
    ) as http:
        await http.get("http://127.0.0.1:8000/redirect", auth=("username", "password"))

    assert events == [
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {"location": "/", "server": "testserver"},
        },
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {"server": "testserver"},
        },
    ]
