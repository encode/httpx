import json
import typing

import click
import pygments.lexers
import pygments.util
import rich.console
import rich.syntax

import httpx


def validate_json(
    ctx: click.Context,
    param: typing.Union[click.Option, click.Parameter],
    value: typing.Any,
) -> typing.Any:
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:  # pragma: nocover
        raise click.BadParameter("Not valid JSON")


def get_lexer_for_response(response: httpx.Response) -> str:
    content_type = response.headers.get("Content-Type")
    if content_type is not None:
        mime_type, _, _ = content_type.partition(";")
        try:
            return pygments.lexers.get_lexer_for_mimetype(mime_type.strip()).name
        except pygments.util.ClassNotFound:  # pragma: nocover
            pass
    return ""  # pragma: nocover


@click.command()
@click.argument("url", type=str)
@click.option("--method", "-m", "method", type=str, default="GET")
@click.option("--params", "-p", "params", type=(str, str), multiple=True)
@click.option("--content", "-c", "content", type=str)
@click.option("--data", "-d", "data", type=(str, str), multiple=True)
@click.option(
    "--files", "-f", "files", type=(str, click.File(mode="rb")), multiple=True
)
@click.option("--json", "-j", "json", type=str, callback=validate_json)
@click.option("--headers", "-h", "headers", type=(str, str), multiple=True)
@click.option("--cookies", "cookies", type=(str, str), multiple=True)
@click.option("--proxies", "-p", "proxies", type=str, default=None)
@click.option("--timeout", "-t", "timeout", type=float, default=5.0)
@click.option("--allow-redirects/--no-allow-redirects", "allow_redirects", default=True)
@click.option("--verify/--no-verify", "verify", default=True)
@click.option("--cert", "cert", type=click.Path(exists=True), default=None)
@click.option("--trust-env/--no-trust-env", "trust_env", default=True)
def httpx_cli(
    url: str,
    method: str,
    params: typing.List[typing.Tuple[str, str]],
    content: str,
    data: typing.List[typing.Tuple[str, str]],
    files: typing.List[typing.Tuple[str, click.File]],
    json: str,
    headers: typing.List[typing.Tuple[str, str]],
    cookies: typing.List[typing.Tuple[str, str]],
    proxies: str,
    timeout: float,
    allow_redirects: bool,
    verify: bool,
    cert: typing.Optional[click.Path],
    trust_env: bool,
) -> None:
    console = rich.console.Console()

    response = httpx.request(
        method,
        url,
        params=list(params),
        data=dict(data),
        files=files,  # type: ignore
        json=json,
        headers=headers,
        cookies=dict(cookies),
        proxies=proxies,
        timeout=timeout,
        allow_redirects=allow_redirects,
        verify=verify,
        cert=None if cert is None else str(cert),
        trust_env=trust_env,
    )

    lexer_name = get_lexer_for_response(response)

    if lexer_name:
        syntax = rich.syntax.Syntax(response.text, lexer_name)
        console.print(syntax)
    else:  # pragma: nocover
        console.print(response.text)
