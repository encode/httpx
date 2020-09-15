import pytest
from click.testing import CliRunner

from httpx._cli.cli import httpx_cli
from httpx._cli.main import main


def splitlines(output):
    return [line.strip() for line in output.splitlines()]


def remove_date_header(lines):
    return [line for line in lines if not line.startswith("date:")]


def test_main():
    with pytest.raises(SystemExit):
        main()


def test_get(server):
    url = str(server.url)
    runner = CliRunner()
    result = runner.invoke(httpx_cli, [url])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "transfer-encoding: chunked",
        "",
        "Hello, world!",
    ]


def test_post(server):
    url = str(server.url.copy_with(path="/echo_body"))
    runner = CliRunner()
    result = runner.invoke(httpx_cli, [url, "-m", "POST", "-j", '{"hello": "world"}'])
    assert result.exit_code == 0
    assert remove_date_header(splitlines(result.output)) == [
        "HTTP/1.1 200 OK",
        "server: uvicorn",
        "content-type: text/plain",
        "transfer-encoding: chunked",
        "",
        '{"hello": "world"}',
    ]
