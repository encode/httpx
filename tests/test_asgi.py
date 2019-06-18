import pytest

import http3


async def hello_world(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_body(scope, receive, send):
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
    raise ValueError()


async def raise_exc_after_response(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    raise ValueError()


def test_asgi():
    client = http3.Client(app=hello_world)
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_asgi_upload():
    client = http3.Client(app=echo_body)
    response = client.post("http://www.example.org/", data=b"example")
    assert response.status_code == 200
    assert response.text == "example"


def test_asgi_exc():
    client = http3.Client(app=raise_exc)
    with pytest.raises(ValueError):
        response = client.get("http://www.example.org/")


def test_asgi_exc_after_response():
    client = http3.Client(app=raise_exc_after_response)
    with pytest.raises(ValueError):
        response = client.get("http://www.example.org/")
