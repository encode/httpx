from urllib.parse import parse_qs

import pytest

from httpcore import (
    Adapter,
    RedirectAdapter,
    RedirectLoop,
    Request,
    Response,
    TooManyRedirects,
    codes,
)


class MockDispatch(Adapter):
    def prepare_request(self, request: Request) -> None:
        pass

    async def send(self, request: Request, **options) -> Response:
        if request.url.path == "/redirect_301":  # "Moved Permanently"
            return Response(301, headers=[(b"location", b"https://example.org/")])

        elif request.url.path == "/redirect_302":  # "Found"
            return Response(302, headers=[(b"location", b"https://example.org/")])

        elif request.url.path == "/redirect_303":  # "See Other"
            return Response(303, headers=[(b"location", b"https://example.org/")])

        elif request.url.path == "/relative_redirect":
            return Response(codes.see_other, headers=[(b"location", b"/")])

        elif request.url.path == "/no_scheme_redirect":
            return Response(codes.see_other, headers=[(b"location", b"//example.org/")])

        elif request.url.path == "/multiple_redirects":
            params = parse_qs(request.url.query)
            count = int(params.get("count", "0")[0])
            code = codes.see_other if count else codes.ok
            location = "/multiple_redirects?count=" + str(count - 1)
            headers = [(b"location", location.encode())] if count else []
            return Response(code, headers=headers)

        if request.url.path == "/redirect_loop":
            return Response(codes.see_other, headers=[(b"location", b"/redirect_loop")])

        return Response(codes.ok, body=b"Hello, world!")


@pytest.mark.asyncio
async def test_redirect_301():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("POST", "https://example.org/redirect_301")
    assert response.status_code == codes.ok


@pytest.mark.asyncio
async def test_redirect_302():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("POST", "https://example.org/redirect_302")
    assert response.status_code == codes.ok


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
async def test_no_scheme_redirect():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/no_scheme_redirect")
    assert response.status_code == codes.ok


@pytest.mark.asyncio
async def test_fragment_redirect():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/relative_redirect#fragment")
    assert response.status_code == codes.ok


@pytest.mark.asyncio
async def test_multiple_redirects():
    client = RedirectAdapter(MockDispatch())
    response = await client.request(
        "GET", "https://example.org/multiple_redirects?count=20"
    )
    assert response.status_code == codes.ok


@pytest.mark.asyncio
async def test_too_many_redirects():
    client = RedirectAdapter(MockDispatch())
    with pytest.raises(TooManyRedirects):
        await client.request("GET", "https://example.org/multiple_redirects?count=21")


@pytest.mark.asyncio
async def test_redirect_loop():
    client = RedirectAdapter(MockDispatch())
    with pytest.raises(RedirectLoop):
        await client.request("GET", "https://example.org/redirect_loop")
