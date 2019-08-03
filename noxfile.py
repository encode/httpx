import nox


@nox.session(python=["3.6", "3.7", "3.8"])
def tests(session):
    session.install("-r", "requirements.txt")
    session.install(".")
    session.run(
        "pytest",
        "--ignore",
        "venv",
        "--cov",
        "tests",
        "--cov",
        "httpx",
        env={"PYTHONPATH": "."},
    )
    session.run("coverage", "report", "--show-missing", "--fail-under=100")


@nox.session
def lint(session):
    session.install("-r", "requirements.txt")
    session.run(
        "flake8",
        "--max-line-length=88",
        "--ignore=W503,E203,B305",
        "httpx",
        "tests",
        "setup.py",
        "noxfile.py",
    )
    session.run("mypy", "httpx", "--ignore-missing-imports", "--disallow-untyped-defs")
