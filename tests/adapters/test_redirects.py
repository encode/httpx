import pytest

from httpcore import Adapter, RedirectAdapter, Request, Response, codes


class MockDispatch(Adapter):
    def prepare_request(self, request: Request) -> None:
        pass

    async def send(self, request: Request, **options) -> Response:
        if request.url.path == "/redirect_303":
            return Response(
                codes.see_other, headers=[(b"location", b"https://example.org/")]
            )
        elif request.url.path == "/relative_redirect":
            return Response(codes.see_other, headers=[(b"location", b"/")])
        return Response(codes.ok, body=b"Hello, world!")


@pytest.mark.asyncio
async def test_redirect_303():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/redirect_303")
    assert response.status_code == codes.ok


@pytest.mark.asyncio
async def test_relative_redirect():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/relative_redirect")
    assert response.status_code == codes.ok
