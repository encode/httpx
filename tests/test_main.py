import os
import typing

from click.testing import CliRunner

import httpx


def splitlines(output: str) -> typing.Iterable[str]:
    return [line.strip() for line in output.splitlines()]


def remove_date_header(lines: typing.Iterable[str]) -> typing.Iterable[str]:
    return [line for line in lines if not line.startswith("date:")]


def test_help():
    runner = CliRunner()
    result = runner.invoke(httpx.main, ["--help"])
    assert result.exit_code == 0
    assert "A next generation HTTP client." in result.output


def test_get(server):
    url = str(server.url)
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "Transfer-Encoding: chunked",
        "",
        "Hello, world!",
    ]


def test_json(server):
    url = str(server.url.copy_with(path="/json"))
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: application/json",
        "Transfer-Encoding: chunked",
        "",
        "{",
        '"Hello": "world!"',
        "}",
    ]


def test_binary(server):
    url = str(server.url.copy_with(path="/echo_binary"))
    runner = CliRunner()
    content = "Hello, world!"
    result = runner.invoke(httpx.main, [url, "-c", content])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: application/octet-stream",
        "Transfer-Encoding: chunked",
        "",
        f"<{len(content)} bytes of binary data>",
    ]


def test_redirects(server):
    url = str(server.url.copy_with(path="/redirect_301"))
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url])
    assert result.exit_code == 1
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 301 Moved Permanently",
        "server: uvicorn",
        "location: /",
        "Transfer-Encoding: chunked",
        "",
    ]


def test_follow_redirects(server):
    url = str(server.url.copy_with(path="/redirect_301"))
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url, "--follow-redirects"])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 301 Moved Permanently",
        "server: uvicorn",
        "location: /",
        "Transfer-Encoding: chunked",
        "",
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "Transfer-Encoding: chunked",
        "",
        "Hello, world!",
    ]


def test_post(server):
    url = str(server.url.copy_with(path="/echo_body"))
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url, "-m", "POST", "-j", '{"hello": "world"}'])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "Transfer-Encoding: chunked",
        "",
        '{"hello":"world"}',
    ]


def test_verbose(server):
    url = str(server.url)
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url, "-v"])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "* Connecting to '127.0.0.1'",
        "* Connected to '127.0.0.1' on port 8000",
        "GET / HTTP/1.1",
        f"Host: {server.url.netloc.decode('ascii')}",
        "Accept: */*",
        "Accept-Encoding: gzip, deflate, br, zstd",
        "Connection: keep-alive",
        f"User-Agent: python-httpx/{httpx.__version__}",
        "",
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "Transfer-Encoding: chunked",
        "",
        "Hello, world!",
    ]


def test_auth(server):
    url = str(server.url)
    runner = CliRunner()
    result = runner.invoke(httpx.main, [url, "-v", "--auth", "username", "password"])
    print(result.output)
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "* Connecting to '127.0.0.1'",
        "* Connected to '127.0.0.1' on port 8000",
        "GET / HTTP/1.1",
        f"Host: {server.url.netloc.decode('ascii')}",
        "Accept: */*",
        "Accept-Encoding: gzip, deflate, br, zstd",
        "Connection: keep-alive",
        f"User-Agent: python-httpx/{httpx.__version__}",
        "Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        "",
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "Transfer-Encoding: chunked",
        "",
        "Hello, world!",
    ]


def test_download(server):
    url = str(server.url)
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(httpx.main, [url, "--download", "index.txt"])
        assert os.path.exists("index.txt")
        with open("index.txt", "r") as input_file:
            assert input_file.read() == "Hello, world!"


def test_errors():
    runner = CliRunner()
    result = runner.invoke(httpx.main, ["invalid://example.org"])
    assert result.exit_code == 1
    assert splitlines(result.output) == [
        "UnsupportedProtocol: Request URL has an unsupported protocol 'invalid://'.",
    ]
