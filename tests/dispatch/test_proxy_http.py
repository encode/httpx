import pytest

import httpx


@pytest.mark.parametrize("status_code", [113, 300, 404, 500])
async def test_proxy_tunnel_error(server, backend, status_code):
    async with httpx.HTTPProxy(
        proxy_url="http://127.0.0.1:8000",
        backend=backend,
        proxy_mode=httpx.HTTPProxyMode.TUNNEL_ONLY,
    ) as proxy:
        response = await proxy.request(
            "GET", f"https://example.org/proxy_status_code/{status_code}"
        )

        assert (
            response.request.url.full_path
            == f"https://example.org/proxy_status_code/{status_code}"
        )
        assert response.status_code == 200
