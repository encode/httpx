import json

import pytest

from httpcore import (
    CertTypes,
    Client,
    Dispatcher,
    Request,
    Response,
    TimeoutTypes,
    VerifyTypes,
)


class MockDispatch(Dispatcher):
    def send(
        self,
        request: Request,
        stream: bool = False,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
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


def test_dispatch_class():
    """
    Use a syncronous 'Dispatcher' class directly.
    """
    url = "https://example.org/"
    with MockDispatch() as dispatcher:
        response = dispatcher.request("GET", url)

    assert response.status_code == 200
    assert response.json() == {"hello": "world"}
