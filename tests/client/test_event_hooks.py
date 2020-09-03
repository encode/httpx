import pytest

import httpx


def test_event_hooks(server):
    events = []

    def on_request(request):
        events.append({"event": "request", "headers": dict(request.headers)})

    def on_response(response):
        headers = dict(response.headers)
        headers["date"] = "Mon, 1 Jan 2020 12:34:56 GMT"
        events.append({"event": "response", "headers": headers})

    event_hooks = {"request": [on_request], "response": [on_response]}

    with httpx.Client(event_hooks=event_hooks) as http:
        http.get(server.url, auth=("username", "password"))

    assert events == [
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {
                "date": "Mon, 1 Jan 2020 12:34:56 GMT",
                "server": "uvicorn",
                "content-type": "text/plain",
                "transfer-encoding": "chunked",
            },
        },
    ]


def test_event_hooks_raising_exception(server):
    def raise_on_4xx_5xx(response):
        response.raise_for_status()

    event_hooks = {"response": [raise_on_4xx_5xx]}

    with httpx.Client(event_hooks=event_hooks) as http:
        url = server.url.copy_with(path="/status/400")
        try:
            http.get(url)
        except httpx.HTTPStatusError as exc:
            assert exc.response.is_closed


@pytest.mark.usefixtures("async_environment")
async def test_async_event_hooks(server):
    events = []

    async def on_request(request):
        events.append({"event": "request", "headers": dict(request.headers)})

    async def on_response(response):
        headers = dict(response.headers)
        headers["date"] = "Mon, 1 Jan 2020 12:34:56 GMT"
        events.append({"event": "response", "headers": headers})

    event_hooks = {"request": [on_request], "response": [on_response]}

    async with httpx.AsyncClient(event_hooks=event_hooks) as http:
        await http.get(server.url, auth=("username", "password"))

    assert events == [
        {
            "event": "request",
            "headers": {
                "host": "127.0.0.1:8000",
                "user-agent": f"python-httpx/{httpx.__version__}",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br",
                "connection": "keep-alive",
                "authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            },
        },
        {
            "event": "response",
            "headers": {
                "date": "Mon, 1 Jan 2020 12:34:56 GMT",
                "server": "uvicorn",
                "content-type": "text/plain",
                "transfer-encoding": "chunked",
            },
        },
    ]


@pytest.mark.usefixtures("async_environment")
async def test_async_event_hooks_raising_exception(server):
    async def raise_on_4xx_5xx(response):
        response.raise_for_status()

    event_hooks = {"response": [raise_on_4xx_5xx]}

    async with httpx.AsyncClient(event_hooks=event_hooks) as http:
        url = server.url.copy_with(path="/status/400")
        try:
            await http.get(url)
        except httpx.HTTPStatusError as exc:
            assert exc.response.is_closed
