import json
from urllib.parse import parse_qs

import pytest

from httpcore import (
    URL,
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
            return Response(
                301, headers=[(b"location", b"https://example.org/")], request=request
            )

        elif request.url.path == "/redirect_302":  # "Found"
            return Response(
                302, headers=[(b"location", b"https://example.org/")], request=request
            )

        elif request.url.path == "/redirect_303":  # "See Other"
            return Response(
                303, headers=[(b"location", b"https://example.org/")], request=request
            )

        elif request.url.path == "/relative_redirect":
            return Response(
                codes.see_other, headers=[(b"location", b"/")], request=request
            )

        elif request.url.path == "/no_scheme_redirect":
            return Response(
                codes.see_other,
                headers=[(b"location", b"//example.org/")],
                request=request,
            )

        elif request.url.path == "/multiple_redirects":
            params = parse_qs(request.url.query)
            count = int(params.get("count", "0")[0])
            redirect_count = count - 1
            code = codes.see_other if count else codes.ok
            location = "/multiple_redirects"
            if redirect_count:
                location += "?count=" + str(redirect_count)
            headers = [(b"location", location.encode())] if count else []
            return Response(code, headers=headers, request=request)

        if request.url.path == "/redirect_loop":
            return Response(
                codes.see_other,
                headers=[(b"location", b"/redirect_loop")],
                request=request,
            )

        elif request.url.path == "/cross_domain":
            location = b"https://example.org/cross_domain_target"
            return Response(301, headers=[(b"location", location)], request=request)

        elif request.url.path == "/cross_domain_target":
            headers = {k.decode(): v.decode() for k, v in request.headers.raw}
            body = json.dumps({"headers": headers}).encode()
            return Response(codes.ok, body=body, request=request)

        return Response(codes.ok, body=b"Hello, world!", request=request)


@pytest.mark.asyncio
async def test_redirect_301():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("POST", "https://example.org/redirect_301")
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_redirect_302():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("POST", "https://example.org/redirect_302")
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_redirect_303():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/redirect_303")
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_relative_redirect():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/relative_redirect")
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_no_scheme_redirect():
    client = RedirectAdapter(MockDispatch())
    response = await client.request("GET", "https://example.org/no_scheme_redirect")
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_fragment_redirect():
    client = RedirectAdapter(MockDispatch())
    response = await client.request(
        "GET", "https://example.org/relative_redirect#fragment"
    )
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/#fragment")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_multiple_redirects():
    client = RedirectAdapter(MockDispatch())
    response = await client.request(
        "GET", "https://example.org/multiple_redirects?count=20"
    )
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/multiple_redirects")
    assert len(response.history) == 20


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


@pytest.mark.asyncio
async def test_cross_domain_redirect():
    client = RedirectAdapter(MockDispatch())
    headers = [(b"Authorization", b"abc")]
    url = "https://example.com/cross_domain"
    response = await client.request("GET", url, headers=headers)
    data = json.loads(response.body.decode())
    assert response.url == URL("https://example.org/cross_domain_target")
    assert data == {"headers": {}}


@pytest.mark.asyncio
async def test_same_domain_redirect():
    client = RedirectAdapter(MockDispatch())
    headers = [(b"Authorization", b"abc")]
    url = "https://example.org/cross_domain"
    response = await client.request("GET", url, headers=headers)
    data = json.loads(response.body.decode())
    assert response.url == URL("https://example.org/cross_domain_target")
    assert data == {"headers": {"authorization": "abc"}}
