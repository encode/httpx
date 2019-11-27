import json

import pytest

from httpx import (
    CertTypes,
    Client,
    Dispatcher,
    QueryParams,
    Request,
    Response,
    TimeoutTypes,
    VerifyTypes,
)
from httpx.models import URL


class MockDispatch(Dispatcher):
    async def send(
        self,
        request: Request,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> Response:
        if request.url.path.startswith("/echo_queryparams"):
            body = json.dumps({"ok": "ok"}).encode()
            return Response(200, content=body, request=request)


def test_client_queryparams():
    client = Client(params={"a": "b"})
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_string():
    client = Client(params="a=b")
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"

    client = Client()
    client.params = "a=b"
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


@pytest.mark.asyncio
async def test_client_queryparams_echo():
    url = "http://example.org/echo_queryparams"
    client_queryparams = "first=str"
    request_queryparams = {"second": "dict"}
    client = Client(dispatch=MockDispatch(), params=client_queryparams)
    response = await client.get(url, params=request_queryparams)

    assert response.status_code == 200
    assert response.url == URL(
        "http://example.org/echo_queryparams?first=str&second=dict"
    )
