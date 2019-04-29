import pytest
from urllib.parse import parse_qs

from httpcore import Adapter, RedirectAdapter, Request, Response, TooManyRedirects, codes


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
        elif request.url.path == "/multiple_redirects":
            params = parse_qs(request.url.query)
            count = int(params.get("count", "0")[0])
            code = codes.see_other if count else codes.ok
            location = "/multiple_redirects?count=" + str(count - 1)
            headers = [(b"location", location.encode())] if count else []
            return Response(code, headers=headers)
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


@pytest.mark.asyncio
async def test_multiple_redirects():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/multiple_redirects?count=20")
    assert response.status_code == codes.ok


@pytest.mark.asyncio
async def test_too_many_redirects():
    client = RedirectAdapter(MockDispatch())
    with pytest.raises(TooManyRedirects):
        await client.request("GET", "https://example.org/multiple_redirects?count=21")
