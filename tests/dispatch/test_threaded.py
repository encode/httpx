import json

from httpx import (
    CertTypes,
    Client,
    Dispatcher,
    HTTPVersionTypes,
    Request,
    Response,
    TimeoutTypes,
    VerifyTypes,
)


def streaming_body():
    for part in [b"Hello", b", ", b"world!"]:
        yield part


class MockDispatch(Dispatcher):
    def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
        http_versions: HTTPVersionTypes = None,
    ) -> Response:
        if request.url.path == "/streaming_response":
            return Response(200, content=streaming_body(), request=request)
        elif request.url.path == "/echo_request_body":
            content = request.read()
            return Response(200, content=content, request=request)
        elif request.url.path == "/echo_request_body_streaming":
            content = b"".join([part for part in request.stream()])
            return Response(200, content=content, request=request)
        else:
            body = json.dumps({"hello": "world"}).encode()
            return Response(200, content=body, request=request)


def test_threaded_dispatch():
    """
    Use a syncronous 'Dispatcher' class with the client.
    Calls to the dispatcher will end up running within a thread pool.
    """
    url = "https://example.org/"
    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"hello": "world"}


def test_threaded_streaming_response():
    url = "https://example.org/streaming_response"
    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_threaded_streaming_request():
    url = "https://example.org/echo_request_body"
    with Client(dispatch=MockDispatch()) as client:
        response = client.post(url, data=streaming_body())

    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_threaded_request_body():
    url = "https://example.org/echo_request_body"
    with Client(dispatch=MockDispatch()) as client:
        response = client.post(url, data=b"Hello, world!")

    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_threaded_request_body_streaming():
    url = "https://example.org/echo_request_body_streaming"
    with Client(dispatch=MockDispatch()) as client:
        response = client.post(url, data=b"Hello, world!")

    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_dispatch_class():
    """
    Use a syncronous 'Dispatcher' class directly.
    """
    url = "https://example.org/"
    with MockDispatch() as dispatcher:
        response = dispatcher.request("GET", url)

    assert response.status_code == 200
    assert response.json() == {"hello": "world"}
