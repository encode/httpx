import pytest

import httpx
from httpx.dispatch.asgi import ASGIDispatch
from tests.compat import nullcontext

from .utils import LifespanSpy


async def hello_world(scope, receive, send):
    assert scope["type"] == "http"
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_body(scope, receive, send):
    assert scope["type"] == "http"
    status = 200
    headers = [(b"content-type", "text/plain")]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    more_body = True
    while more_body:
        message = await receive()
        body = message.get("body", b"")
        more_body = message.get("more_body", False)
        await send({"type": "http.response.body", "body": body, "more_body": more_body})


async def raise_exc(scope, receive, send):
    assert scope["type"] == "http"
    raise ValueError()


async def raise_exc_after_response(scope, receive, send):
    assert scope["type"] == "http"
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise ValueError()


def test_asgi():
    client = httpx.Client(app=hello_world)
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


async def test_asgi_async(backend):
    client = httpx.AsyncClient(app=hello_world, backend=backend)
    response = await client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_asgi_upload():
    client = httpx.Client(app=echo_body)
    response = client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


async def test_asgi_upload_async(backend):
    client = httpx.AsyncClient(app=echo_body, backend=backend)
    response = await client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


def test_asgi_exc():
    client = httpx.Client(app=raise_exc)
    with pytest.raises(ValueError):
        client.get("http://www.example.org/")


async def test_asgi_exc_async(backend):
    client = httpx.AsyncClient(app=raise_exc, backend=backend)
    with pytest.raises(ValueError):
        await client.get("http://www.example.org/")


def test_asgi_exc_after_response():
    client = httpx.Client(app=raise_exc_after_response)
    with pytest.raises(ValueError):
        client.get("http://www.example.org/")


async def test_asgi_exc_after_response_async(backend):
    client = httpx.AsyncClient(app=raise_exc_after_response, backend=backend)
    with pytest.raises(ValueError):
        await client.get("http://www.example.org/")


class FakeAppException(Exception):
    pass


@pytest.mark.parametrize("handle_startup_failed", (True, False))
@pytest.mark.parametrize("startup_exception", (None, FakeAppException))
@pytest.mark.parametrize("raise_app_exceptions", (True, False))
async def test_asgi_lifespan(
    backend, raise_app_exceptions, startup_exception, handle_startup_failed
):
    app = LifespanSpy(
        hello_world,
        startup_exception=startup_exception,
        handle_startup_failed=handle_startup_failed,
    )

    should_run_lifespan = (
        not startup_exception or handle_startup_failed or raise_app_exceptions
    )

    with (
        pytest.raises(FakeAppException)
        if startup_exception and not handle_startup_failed and raise_app_exceptions
        else nullcontext()
    ):
        async with ASGIDispatch(
            app, backend=backend, raise_app_exceptions=raise_app_exceptions
        ) as http:
            assert app.received_lifespan_events.pop() == "lifespan.startup"
            with (
                pytest.raises(IndexError) if not should_run_lifespan else nullcontext()
            ):
                assert app.sent_lifespan_events.pop() == (
                    f"lifespan.startup.{'failed' if startup_exception else 'complete'}"
                )

            response = await http.request("GET", "http://www.example.org/")
            await response.read()
            assert response.status_code == 200

        with pytest.raises(IndexError) if not should_run_lifespan else nullcontext():
            assert app.received_lifespan_events.pop() == "lifespan.shutdown"

        with pytest.raises(IndexError) if not should_run_lifespan else nullcontext():
            assert app.sent_lifespan_events.pop() == "lifespan.shutdown.complete"


async def test_asgi_lifespan_unsupported(backend):
    async with ASGIDispatch(app=hello_world, backend=backend) as http:
        response = await http.request("GET", "http://www.example.org/")
        await response.read()
        assert response.status_code == 200
