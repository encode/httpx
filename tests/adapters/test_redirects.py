import json
from urllib.parse import parse_qs

import pytest

from httpcore import (
    URL,
    Adapter,
    RedirectAdapter,
    RedirectBodyUnavailable,
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
        if request.url.path == "/redirect_301":
            status_code = codes.moved_permanently
            headers = {"location": "https://example.org/"}
            return Response(status_code, headers=headers, request=request)

        elif request.url.path == "/redirect_302":
            status_code = codes.found
            headers = {"location": "https://example.org/"}
            return Response(status_code, headers=headers, request=request)

        elif request.url.path == "/redirect_303":
            status_code = codes.see_other
            headers = {"location": "https://example.org/"}
            return Response(status_code, headers=headers, request=request)

        elif request.url.path == "/relative_redirect":
            headers = {"location": "/"}
            return Response(codes.see_other, headers=headers, request=request)

        elif request.url.path == "/no_scheme_redirect":
            headers = {"location": "//example.org/"}
            return Response(codes.see_other, headers=headers, request=request)

        elif request.url.path == "/multiple_redirects":
            params = parse_qs(request.url.query)
            count = int(params.get("count", "0")[0])
            redirect_count = count - 1
            code = codes.see_other if count else codes.ok
            location = "/multiple_redirects"
            if redirect_count:
                location += "?count=" + str(redirect_count)
            headers = {"location": location} if count else {}
            return Response(code, headers=headers, request=request)

        if request.url.path == "/redirect_loop":
            headers = {"location": "/redirect_loop"}
            return Response(codes.see_other, headers=headers, request=request)

        elif request.url.path == "/cross_domain":
            headers = {"location": "https://example.org/cross_domain_target"}
            return Response(codes.see_other, headers=headers, request=request)

        elif request.url.path == "/cross_domain_target":
            headers = dict(request.headers.items())
            content = json.dumps({"headers": headers}).encode()
            return Response(codes.ok, content=content, request=request)

        elif request.url.path == "/redirect_body":
            await request.read()
            headers = {"location": "/redirect_body_target"}
            return Response(codes.permanent_redirect, headers=headers, request=request)

        elif request.url.path == "/redirect_body_target":
            content = await request.read()
            body = json.dumps({"body": content.decode()}).encode()
            return Response(codes.ok, content=body, request=request)

        return Response(codes.ok, content=b"Hello, world!", request=request)


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
async def test_disallow_redirects():
    client = RedirectAdapter(MockDispatch())
    response = await client.request(
        "POST", "https://example.org/redirect_303", allow_redirects=False
    )
    assert response.status_code == codes.see_other
    assert response.url == URL("https://example.org/redirect_303")
    assert len(response.history) == 0

    response = await response.next()
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
    url = "https://example.org/relative_redirect#fragment"
    response = await client.request("GET", url)
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/#fragment")
    assert len(response.history) == 1


@pytest.mark.asyncio
async def test_multiple_redirects():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.org/multiple_redirects?count=20"
    response = await client.request("GET", url)
    assert response.status_code == codes.ok
    assert response.url == URL("https://example.org/multiple_redirects")
    assert len(response.history) == 20


@pytest.mark.asyncio
async def test_too_many_redirects():
    client = RedirectAdapter(MockDispatch())
    with pytest.raises(TooManyRedirects):
        await client.request("GET", "https://example.org/multiple_redirects?count=21")


@pytest.mark.asyncio
async def test_too_many_redirects_calling_next():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.org/multiple_redirects?count=21"
    response = await client.request("GET", url, allow_redirects=False)
    with pytest.raises(TooManyRedirects):
        while response.is_redirect:
            response = await response.next()


@pytest.mark.asyncio
async def test_redirect_loop():
    client = RedirectAdapter(MockDispatch())
    with pytest.raises(RedirectLoop):
        await client.request("GET", "https://example.org/redirect_loop")


@pytest.mark.asyncio
async def test_redirect_loop_calling_next():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.org/redirect_loop"
    response = await client.request("GET", url, allow_redirects=False)
    with pytest.raises(RedirectLoop):
        while response.is_redirect:
            response = await response.next()


@pytest.mark.asyncio
async def test_cross_domain_redirect():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.com/cross_domain"
    headers = {"Authorization": "abc"}
    response = await client.request("GET", url, headers=headers)
    data = json.loads(response.content.decode())
    assert response.url == URL("https://example.org/cross_domain_target")
    assert data == {"headers": {}}


@pytest.mark.asyncio
async def test_same_domain_redirect():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.org/cross_domain"
    headers = {"Authorization": "abc"}
    response = await client.request("GET", url, headers=headers)
    data = json.loads(response.content.decode())
    assert response.url == URL("https://example.org/cross_domain_target")
    assert data == {"headers": {"authorization": "abc"}}


@pytest.mark.asyncio
async def test_body_redirect():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.org/redirect_body"
    content = b"Example request body"
    response = await client.request("POST", url, content=content)
    data = json.loads(response.content.decode())
    assert response.url == URL("https://example.org/redirect_body_target")
    assert data == {"body": "Example request body"}


@pytest.mark.asyncio
async def test_cannot_redirect_streaming_body():
    client = RedirectAdapter(MockDispatch())
    url = "https://example.org/redirect_body"

    async def streaming_body():
        yield b"Example request body"

    with pytest.raises(RedirectBodyUnavailable):
        await client.request("POST", url, content=streaming_body())
