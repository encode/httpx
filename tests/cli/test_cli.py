import pytest
from click.testing import CliRunner

from httpx._cli.cli import httpx_cli
from httpx._cli.main import main


def splitlines(output):
    return [line.strip() for line in output.splitlines()]


def test_main():
    with pytest.raises(SystemExit):
        main()


def test_get(server):
    url = str(server.url)
    runner = CliRunner()
    result = runner.invoke(httpx_cli, [url])
    assert result.exit_code == 0
    assert splitlines(result.output) == ["Hello, world!"]


def test_post(server):
    url = str(server.url.copy_with(path="/echo_body"))
    runner = CliRunner()
    result = runner.invoke(httpx_cli, [url, "-m", "POST", "-j", '{"hello": "world"}'])
    assert result.exit_code == 0
    assert splitlines(result.output) == ['{"hello": "world"}']
