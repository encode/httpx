import nox

source_files = ("httpx", "tests", "setup.py", "noxfile.py")


@nox.session(reuse_venv=True)
def lint(session):
    session.install("autoflake", "black", "flake8", "isort", "seed-isort-config")

    session.run("autoflake", "--in-place", "--recursive", *source_files)
    session.run("seed-isort-config", "--application-directories=httpx")
    session.run(
        "isort",
        "--project=httpx",
        "--multi-line=3",
        "--trailing-comma",
        "--force-grid-wrap=0",
        "--combine-as",
        "--line-width=88",
        "--recursive",
        "--apply",
        *source_files,
    )
    session.run("black", "--target-version=py36", *source_files)

    check(session)


@nox.session(reuse_venv=True)
def check(session):
    session.install("black", "flake8", "flake8-bugbear", "mypy")

    session.run("black", "--check", "--target-version=py36", *source_files)
    session.run(
        "flake8", "--max-line-length=88", "--ignore=W503,E203,B305", *source_files
    )
    session.run("mypy", "httpx", "--ignore-missing-imports", "--disallow-untyped-defs")


@nox.session(reuse_venv=True)
def docs(session):
    session.install("mkdocs", "mkdocs-material")

    session.run("mkdocs", "build")


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.install("-r", "test-requirements.txt")

    session.run(
        "coverage",
        "run",
        "--omit='*'",
        "-m",
        "pytest",
        "--cov=httpx",
        "--cov=tests",
        "--cov-report=term-missing",
    )
