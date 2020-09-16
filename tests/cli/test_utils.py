import httpx
from httpx._cli.utils import filename_from_content_disposition, filename_from_url


def test_filename_from_content_disposition():
    response = httpx.Response(
        200, headers={"Content-Disposition": "attachment; filename=example.tar.gz"}
    )
    assert filename_from_content_disposition(response) == "example.tar.gz"

    response = httpx.Response(200, headers={})
    assert filename_from_content_disposition(response) == ""


def test_filename_from_url():
    request = httpx.Request("GET", "http://www.example.com/")
    response = httpx.Response(
        200, headers={"Content-Type": "text/html"}, request=request
    )
    assert filename_from_url(response) == "index.html"

    request = httpx.Request("GET", "http://www.example.com/")
    response = httpx.Response(
        200, headers={"Content-Type": "application/json"}, request=request
    )
    assert filename_from_url(response) == "index.json"

    request = httpx.Request("GET", "http://www.example.com/test/")
    response = httpx.Response(
        200, headers={"Content-Type": "application/json"}, request=request
    )
    assert filename_from_url(response) == "test.json"

    request = httpx.Request("GET", "http://www.example.com/test.json")
    response = httpx.Response(
        200, headers={}, request=request
    )
    assert filename_from_url(response) == "test.json"

    request = httpx.Request("GET", "http://www.example.com/")
    response = httpx.Response(200, headers={}, request=request)
    assert filename_from_url(response) == "index"
