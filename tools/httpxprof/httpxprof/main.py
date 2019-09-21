import os
import subprocess

import click

from .config import OUTPUT_DIR, SCRIPTS_DIR, SERVER_HOST, SERVER_PORT
from .utils import server

SCRIPTS = [
    filename.rstrip(".py")
    for filename in os.listdir(SCRIPTS_DIR)
    if filename != "__init__.py"
]


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("script", type=click.Choice(SCRIPTS))
def run(script: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    out = str(OUTPUT_DIR / f"{script}.prof")
    target = str(SCRIPTS_DIR / f"{script}.py")

    args = ["python", "-m", "cProfile", "-o", out, target]

    with server(host=SERVER_HOST, port=SERVER_PORT):
        subprocess.run(args)


@cli.command()
@click.argument("script", type=click.Choice(SCRIPTS))
def view(script: str) -> None:
    args = ["snakeviz", str(OUTPUT_DIR / f"{script}.prof")]
    subprocess.run(args)


if __name__ == "__main__":
    import sys

    sys.exit(cli())
