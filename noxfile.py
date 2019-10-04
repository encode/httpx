import pathlib
import re
import tarfile
import zipfile

import nox

nox.options.stop_on_first_error = True

source_files = ("httpx", "tools", "tests", "setup.py", "noxfile.py")


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
        "black",
        "flake8",
        "flake8-bugbear",
        "flake8-comprehensions",
        "flake8-pie",
        "isort",
        "mypy",
    )

    session.run("black", "--check", "--diff", "--target-version=py36", *source_files)
    session.run("flake8", *source_files)
    session.run("mypy", "httpx")
    session.run(
        "isort", "--check", "--diff", "--project=httpx", "--recursive", *source_files
    )


@nox.session(reuse_venv=True)
def docs(session):
    session.install("mkdocs", "mkdocs-material")

    session.run("mkdocs", "build")


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.install("-r", "test-requirements.txt")
    session.run("python", "-m", "pytest", *session.posargs)


@nox.session(reuse_venv=True)
def check_dist(session):
    output = session.run("python", "setup.py", "sdist", "bdist_wheel", silent=True)
    assert (
        re.search(r"(?m)^copying httpx/py\.typed -> httpx-[^/]+/httpx$", output)
        is not None
    )
    assert (
        re.search(
            r"(?m)^copying build/lib/httpx/py\.typed -> "
            r"build/bdist\.[^/]+/wheel/httpx$",
            output,
        )
        is not None
    )
    assert re.search(r"(?m)^adding 'httpx/py\.typed'$", output) is not None

    def tgz_has_py_typed(p: pathlib.Path) -> bool:
        with tarfile.open(p) as sdist:
            return any(
                re.match(r"httpx-[^/]+/httpx/py\.typed", member.name)
                for member in sdist
            )

    def whl_has_py_typed(p: pathlib.Path) -> bool:
        with zipfile.ZipFile(p) as whl:
            return whl.getinfo("httpx/py.typed").file_size == 0

    dist_dir = pathlib.Path("dist")
    assert [tgz_has_py_typed(sdist) for sdist in dist_dir.glob("**/*.tar.gz")] == [True]
    assert [whl_has_py_typed(whl) for whl in dist_dir.glob("**/*.whl")] == [True]
