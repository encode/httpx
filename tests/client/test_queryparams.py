import json

from httpx import (
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    QueryParams,
    TimeoutTypes,
    VerifyTypes,
)
from httpx.models import URL


class MockDispatch(AsyncDispatcher):
    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        if request.url.path.startswith("/echo_queryparams"):
            body = json.dumps({"ok": "ok"}).encode()
            return AsyncResponse(200, content=body, request=request)


def test_client_queryparams():
    client = Client(params={"a": "b"})
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_string():
    client = Client(params="a=b")
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


def test_client_queryparams_echo():
    url = "http://example.org/echo_queryparams"
    client_queryparams = "first=str"
    request_queryparams = {"second": "dict"}
    with Client(dispatch=MockDispatch(), params=client_queryparams) as client:
        response = client.get(url, params=request_queryparams)

    assert response.status_code == 200
    assert response.url == URL(
        "http://example.org/echo_queryparams?first=str&second=dict"
    )
