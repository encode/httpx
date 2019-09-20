import os
import pathlib
import subprocess

import click
import uvicorn

from .utils import app, timeit

OUTPUT_DIR = pathlib.Path(__file__).parent / "out"
BENCHES_DIR = pathlib.Path(__file__).parent / "benches"
assert BENCHES_DIR.exists(), BENCHES_DIR

BENCHES = [filename.rstrip(".py") for filename in os.listdir(BENCHES_DIR)]


@click.group()
def cli() -> None:
    pass


@cli.command()
def serve() -> None:
    config = uvicorn.Config(app=app)
    server = uvicorn.Server(config)
    server.run()


@cli.command()
@click.argument("bench", type=click.Choice(BENCHES))
def run(bench: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    out = str(OUTPUT_DIR / f"{bench}.prof")
    script = str(BENCHES_DIR / f"{bench}.py")

    args = ["python", "-m", "cProfile", "-o", out, script]

    with timeit():
        subprocess.run(args)


@cli.command()
@click.argument("bench", type=click.Choice(BENCHES))
def view(bench: str) -> None:
    args = ["snakeviz", str(OUTPUT_DIR / f"{bench}.prof")]
    subprocess.run(args)


if __name__ == "__main__":
    import sys

    sys.exit(cli())
