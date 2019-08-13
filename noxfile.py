import nox

source_files = ("httpx", "tests", "setup.py", "noxfile.py")


@nox.session(reuse_venv=True)
def lint(session):
    session.install("autoflake", "black", "flake8", "isort", "seed-isort-config")

    session.run("autoflake", "--in-place", "--recursive", *source_files)
    session.run("seed-isort-config", "--application-directories=httpx")
    session.run("isort", "--project=httpx", "--recursive", "--apply", *source_files)
    session.run("black", "--target-version=py36", *source_files)

    check(session)


@nox.session(reuse_venv=True)
def check(session):
    session.install(
        "black", "flake8", "flake8-bugbear", "flake8-comprehensions", "mypy"
    )

    session.run("black", "--check", "--target-version=py36", *source_files)
    session.run("flake8", *source_files)
    session.run("mypy", "httpx")


@nox.session(reuse_venv=True)
def docs(session):
    session.install("mkdocs", "mkdocs-material")

    session.run("mkdocs", "build")


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.install("-r", "test-requirements.txt")

    session.run("coverage", "run", "-m", "pytest")
