import json

import click
import pygments.lexers
import pygments.util
import rich.console
import rich.syntax

import httpx


def validate_json(ctx, param, value) -> typing.Any:
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise click.BadParameter("Not valid JSON")


@click.command()
@click.argument("url", type=str)
@click.option("--method", "-m", "method", type=str, default="GET")
@click.option("--params", "-p", "params", type=(str, str), multiple=True)
@click.option("--data", "-d", "data", type=(str, str), multiple=True)
@click.option(
    "--files", "-f", "files", type=(str, click.File(mode="rb")), multiple=True
)
@click.option("--json", "-j", "json", type=str, callback=validate_json)
@click.option("--headers", "-h", "headers", type=(str, str), multiple=True)
@click.option("--cookies", "-c", "cookies", type=(str, str), multiple=True)
@click.option("--proxies", "-p", "proxies", type=str, default=None)
@click.option("--timeout", "-t", "timeout", type=float, default=5.0)
@click.option("--allow-redirects/--no-allow-redirects", "allow_redirects", default=True)
@click.option("--verify/--no-verify", "verify", default=True)
@click.option("--cert", "cert", type=click.Path(exists=True), default=None)
@click.option("--trust-env/--no-trust-env", "trust_env", default=True)
def httpx_cli(
    url,
    method,
    params,
    data,
    files,
    json,
    headers,
    cookies,
    proxies,
    timeout,
    allow_redirects,
    verify,
    cert,
    trust_env,
) -> None:
    console = rich.console.Console()

    response = httpx.request(
        method,
        url,
        params=params,
        data=data,
        files=files,
        json=json,
        headers=headers,
        cookies=dict(cookies),
        proxies=proxies,
        timeout=timeout,
        allow_redirects=allow_redirects,
        verify=verify,
        cert=cert,
        trust_env=trust_env,
    )

    content_type = response.headers.get("Content-Type")
    if content_type is not None:
        mime_type, _, _ = content_type.partition(";")
        try:
            lexer_name = pygments.lexers.get_lexer_for_mimetype(mime_type.strip()).name
        except pygments.util.ClassNotFound:
            lexer_name = ""
    else:
        lexer_name = ""

    if lexer_name:
        syntax = rich.syntax.Syntax(response.text, lexer_name)
        console.print(syntax)
    else:
        console.print(response.text)
