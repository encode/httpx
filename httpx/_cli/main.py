import sys


def main() -> None:  # pragma: nocover
    try:
        import click  # noqa
        import rich  # noqa
    except ImportError:
        sys.exit(
            "Attempted to run the HTTPX client, but the required dependancies"
            "are not installed. Use `pip install httpx[cli]`"
        )

    from httpx._cli.cli import httpx_cli

    httpx_cli(["--help"])
