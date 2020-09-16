import json
import sys
import typing

import click
import rich.console
import rich.syntax

import httpx

from .utils import (
    format_request_headers,
    format_response_headers,
    get_lexer_for_response,
)


def show_request_headers(request: httpx.Request) -> None:
    console = rich.console.Console()
    http_text = format_request_headers(request)
    syntax = rich.syntax.Syntax(http_text, "http")
    console.print(syntax)


def show_response_headers(response: httpx.Response) -> None:
    console = rich.console.Console()
    http_text = format_response_headers(response)
    syntax = rich.syntax.Syntax(http_text, "http")
    console.print(syntax)


def print_delimiter(*args: typing.Any) -> None:
    console = rich.console.Console()
    syntax = rich.syntax.Syntax("", "http")
    console.print(syntax)


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


@click.command()
@click.argument("url", type=str)
@click.option(
    "--method",
    "-m",
    "method",
    type=str,
    default="GET",
    help=(
        "Request method, such as GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD. "
        "[Default: GET]"
    ),
)
@click.option(
    "--params",
    "-p",
    "params",
    type=(str, str),
    multiple=True,
    help="Query parameters to include in the request URL.",
)
@click.option(
    "--content",
    "-c",
    "content",
    type=str,
    help="Byte content to include in the request body.",
)
@click.option(
    "--data",
    "-d",
    "data",
    type=(str, str),
    multiple=True,
    help="Form data to include in the request body.",
)
@click.option(
    "--files",
    "-f",
    "files",
    type=(str, click.File(mode="rb")),
    multiple=True,
    help="Form files to include in the request body.",
)
@click.option(
    "--json",
    "-j",
    "json",
    type=str,
    callback=validate_json,
    help="JSON data to include in the request body.",
)
@click.option(
    "--headers",
    "-h",
    "headers",
    type=(str, str),
    multiple=True,
    help="Include additional HTTP headers in the request.",
)
@click.option(
    "--cookies",
    "cookies",
    type=(str, str),
    multiple=True,
    help="Cookies to include in the request.",
)
@click.option(
    "--proxies",
    "-p",
    "proxies",
    type=str,
    default=None,
    help="Send the request via a proxy. Should be the URL giving the proxy address.",
)
@click.option(
    "--timeout",
    "-t",
    "timeout",
    type=float,
    default=5.0,
    help=(
        "Timeout value to use for network operations, such as establishing the "
        "connection, reading some data, etc... [Default: 5.0]"
    ),
)
@click.option(
    "--no-allow-redirects",
    "allow_redirects",
    is_flag=True,
    default=True,
    help="Don't automatically follow redirects.",
)
@click.option(
    "--no-verify",
    "verify",
    is_flag=True,
    default=True,
    help="Disable SSL verification.",
)
@click.option(
    "--http2",
    "http2",
    type=bool,
    is_flag=True,
    default=False,
    help="Send the request using HTTP/2, if the remote server supports it.",
)
@click.option(
    "--verbose",
    "-v",
    type=bool,
    is_flag=True,
    default=False,
    help="Verbose. Show request as well as response.",
)
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
    http2: bool,
    verbose: bool,
) -> None:
    """
    An HTTP command line client.

    Sends a request and displays the response.
    """
    console = rich.console.Console()
    syntax = rich.syntax.Syntax("", "http")

    if verbose:
        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = {
            "request": [show_request_headers],
            "response": [print_delimiter, show_response_headers],
        }
    else:
        event_hooks = {"request": [], "response": [show_response_headers]}

    try:
        client = httpx.Client(
            proxies=proxies,
            timeout=timeout,
            verify=verify,
            http2=http2,
            event_hooks=event_hooks,
        )
        with client.stream(
            method,
            url,
            params=list(params),
            data=dict(data),
            files=files,  # type: ignore
            json=json,
            headers=headers,
            cookies=dict(cookies),
            allow_redirects=allow_redirects,
        ) as response:
            response.read()
            syntax = rich.syntax.Syntax("", "http")
            console.print(syntax)

            lexer_name = get_lexer_for_response(response)
            if lexer_name:
                syntax = rich.syntax.Syntax(response.text, lexer_name)
                console.print(syntax)
            else:  # pragma: nocover
                console.print(response.text)
    except httpx.RequestError as exc:
        console.print(f"{type(exc).__name__}: {exc}")
        sys.exit(1)
