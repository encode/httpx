import ssl
import urllib

import pytest

from httpx._core import AsyncConnectionPool, RawRequest, RawURL


def parse(url_string: str) -> RawURL:
    parsed = urllib.parse.urlparse(url_string)
    scheme = parsed.scheme.encode("ascii")
    host = (parsed.hostname or "").encode("ascii")
    port = parsed.port
    path = parsed.path or "/"
    target = f"{path}?{parsed.query}".rstrip("?").encode("ascii")
    return RawURL(scheme, host, port, target)


@pytest.mark.trio
async def test_request(httpbin):
    async with AsyncConnectionPool() as pool:
        url = parse(httpbin.url)
        request = RawRequest(b"GET", url, [(b"Host", url.host)])
        async with await pool.handle_async_request(request) as response:
            assert response.status == 200


@pytest.mark.trio
async def test_https_request(httpbin_secure):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with AsyncConnectionPool(ssl_context=ssl_context) as pool:
        url = parse(httpbin_secure.url)
        request = RawRequest(b"GET", url, [(b"Host", url.host)])
        async with await pool.handle_async_request(request) as response:
            assert response.status == 200
